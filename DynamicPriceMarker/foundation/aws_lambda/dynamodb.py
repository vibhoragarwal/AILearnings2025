""" DynamoDB interface

There is room for improvement with general exception handlling on each action performed

"""
import os
import decimal
import logging
import time
import uuid
import json
import boto3
from typing import Tuple, List

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import DYNAMODB_CONTEXT
from foundation.utils.customexceptions import (
    ItemNotFound,
    ValidationError,
    ActionNotAllowed,
    ConfigurationError,
)
from foundation.utils.featurebroker import FeatureBroker
from foundation.utils.utils import log_time_spend
from foundation.utils.jwtencoder import is_anon_user_id


logger = logging.getLogger("nest.database")

# Monkey-patch boto3's DynamoDB Decimal context to prevent Inexact and Rounded exceptions
DYNAMODB_CONTEXT.traps[decimal.Inexact] = 0
DYNAMODB_CONTEXT.traps[decimal.Rounded] = 0

decimal_context = decimal.Context(
    Emin=-93,
    Emax=125,
    rounding=decimal.ROUND_HALF_UP,
    prec=38,
    traps=[
        # decimal.Clamped,
        # decimal.Inexact,
        decimal.Overflow,
        # decimal.Rounded,
        decimal.Underflow,
    ],
)


def convert_to_internal(json_data):
    """Convert data to database format

    Note that this is a recursive function. It calls convert also for any contained dictionary or list
    In this particular case, doubles are translated into decimals and None values, empty strings and empty sets
    are removed.

    Args:
        json_data: entry that needs to be converted to database internal format
    Returns:
        Converted values

    @ingroup aws_lambda
    """
    # pylint: disable=too-many-return-statements
    # Recurse nested dictionaries
    if isinstance(json_data, dict):
        # Remove empty strings - Dynamo does not support this
        converted_values = {}
        try:
            for key, value in json_data.items():
                converted_values[key] = convert_to_internal(value)
        except decimal.Overflow as exc_overflow:
            raise ValidationError(
                None,
                {
                    "field": key,
                    "status": "validation error",
                    "message": f"Value {value} too big for DynamoDB (>1e125)",
                },
            ) from exc_overflow
        except decimal.Underflow as exc_underflow:
            raise ValidationError(
                None,
                {
                    "field": key,
                    "status": "validation error",
                    "message": f"Value {value} too close to 0 for DynamoDB (<1e-130)",
                },
            ) from exc_underflow
        return {
            key: value for key, value in converted_values.items() if value is not None
        }
    # Recurse iterables
    if isinstance(json_data, list):
        converted_values = [convert_to_internal(value) for value in json_data]
        return [value for value in converted_values if value is not None]
    # Recurse sets and remove empty sets
    if isinstance(json_data, set):
        converted_values = set(convert_to_internal(value) for value in json_data)
        return set(value for value in converted_values if value is not None) or None
    # Convert float to Decimal
    if isinstance(json_data, (float, int)):
        # Also perform dummy conversion for ints to test if they fit into decimal context limits
        # However, don't convert int to Decimal
        dec = decimal_context.create_decimal(str(json_data))
        if isinstance(json_data, float):
            return dec
        return json_data
    if not json_data and isinstance(json_data, str):
        return None

    # Keep other values the same
    return json_data


def convert_to_dict(internal_data):
    """Convert data from database format

    Note that this is a recursive function. It calls convert also for any contained dictionary or list
    In this particular case, decimals are translated into doubles

    Args:
        internal_data: entry that needs to be converted from database internal format

    Returns:
        Converted values

    @ingroup aws_lambda
    """
    # Recurse nested dictionaries
    if isinstance(internal_data, dict):
        return {key: convert_to_dict(value) for key, value in internal_data.items()}
    # Recurse iterables
    if isinstance(internal_data, list):
        return [convert_to_dict(value) for value in internal_data]
    # Convert Decimal to int or float
    if isinstance(internal_data, decimal.Decimal):
        if int(internal_data) == internal_data:
            return int(internal_data)
        return float(internal_data)
    # Keep other values the same
    return internal_data


def convert_to_dict_filtered(internal_data, skip):
    """Convert data from database format

    Note that this is a recursive function. It calls convert also for any contained dictionary or list
    In this particular case, decimals are translated into doubles

    Args:
        internal_data: entry that needs to be converted from database internal format
        skip: list with fields to sKip certain fields at root level
    Returns:
        Converted values

    @ingroup aws_lambda
    """
    # Recurse nested dictionaries
    if isinstance(internal_data, dict):
        return {
            key: convert_to_dict(value)
            for key, value in internal_data.items()
            if key not in skip
        }
    return convert_to_dict(internal_data)


def check_user(model, user):
    """Check that loaded model user matched given user or is anonymous while user is not"""
    if "userId" not in model:
        # No user in model - so there is nothing to check - that is OK by design
        return True

    if model["userId"] == user:
        return True

    if not is_anon_user_id(user) and is_anon_user_id(model["userId"]):
        print(
            json.dumps(
                {
                    "warning": "User mismatch",
                    "action": "User ID Change",
                    "from": model["userId"],
                    "to": user,
                    "modelId": model.get("id"),
                }
            )
        )
        return True
    # in all other situations - no match
    print(
        json.dumps(
            {
                "warning": "User mismatch",
                "action": "Change not allowed",
                "from": model["userId"],
                "to": user,
                "modelId": model.get("id"),
            }
        )
    )
    return False


def dynamo_exception(func):
    """Wraps a function to provide uniform exception handling for boto3 exceptions"""

    def wrapper(self, *args, **kwargs):
        try:
            # This is a check to see if the resource actually exists
            return func(self, *args, **kwargs)
        except ClientError as client_error:
            if client_error.response["Error"]["Code"] == "ResourceNotFoundException":
                print(
                    f"Table not found: {self.dbname}. Are you running on the right environment?"
                )
                print(os.environ.get("* AWS_SECRET_ACCESS_KEY", "no access key"))
                print(os.environ.get("* AWS_DEFAULT_PROFILE", "no default profile"))
                raise ConfigurationError(
                    self.dbname, "Resource not found"
                ) from client_error
            if client_error.response["Error"]["Code"] == "'AccessDeniedException'":
                print(
                    f"No access to table: {self.dbname}. Are you running on the right environment?"
                )
                raise ConfigurationError(
                    self.dbname, "No access to table"
                ) from client_error

            if client_error.response["Error"]["Code"] == "ExpiredTokenException":
                err_msg = client_error.response["Error"]["Message"]
                print(f"Token expired - please renew you access credentials: {err_msg}")
                raise ActionNotAllowed(
                    "Expired token. Please renew your token"
                ) from client_error
            if (
                client_error.response["Error"]["Code"]
                == "ProvisionedThroughputExceededException"
            ):
                err_msg = client_error.response["Error"]["Message"]
                print("Provisioned throughput exceeded - please try again later")
                raise ActionNotAllowed("Too busy") from client_error
            if (
                client_error.response["Error"]["Code"]
                == "ItemCollectionSizeLimitExceededException"
            ):
                err_msg = client_error.response["Error"]["Message"]
                print("Size limit exceeded")
                raise ConfigurationError(
                    self.dbname, "Data section too big for  the current configuration"
                ) from client_error
            if (
                client_error.response["Error"]["Code"]
                == "ConditionalCheckFailedException"
            ):
                print("Conditional check failed")
                # Can be of owership check failed, or sequence check failed
                # For now send an Action now allowed
                raise ActionNotAllowed from client_error
            raise

    return wrapper


class DynamoDB:
    """
    Generic database wrapper for AWSs DynamoDB
    @ingroup aws_lambda
    """

    ## Cached table static resource containing tablename table mapping
    tables = {}

    resource_instance = None

    def __init__(self, settings):
        """Constructor for the database
        Args:
            settings: containing the configuration options to connect to the database
        """
        ## The network configuration settings for this database
        self.settings = settings
        ## Convenience variable to contain the database name
        self.dbname = self.settings["dbname"]
        ## Attribute name for (optional) item TTL (Time-to-live) timestamp
        self.ttl_attribute_name = self.settings.get("ttl_attribute_name", "expires")
        ## Duration after item creation in days for (optional) item TTL (Time-to-live)
        self.ttl_days = self.settings.get("ttl_days", 7)
        logger.info("Connecting to database %s", self.dbname)

    # ####################################
    # Public methods - part of interface
    # ####################################

    def is_connected(self):
        """Test if the database is accessible right now
        Returns:
            True if database is accessible, False otherwise
        """
        return bool(self.get_dynamo_table())

    @log_time_spend("dynamo-find-item")
    @dynamo_exception
    def find_item(self, my_id):
        """Return the item from the database for the current user

        There is a situation where the model might be owned by another user, and that is when the user decides to
        log in after model created. In that case we have a model created by an anonymous user but needs to be assigned
        to registered user.

        Args:
            my_id: id of item to be found
        Returns:
             the item in DICT format
        """
        logger.info("Looking in %s for %s", self.dbname, my_id)
        table = self.get_dynamo_table()

        # TODO check on filtering based on user
        # query_data = {"idIndex": my_id}
        logger.info("Querying for data in %s: %s", self.dbname, my_id)
        print(
            f"Querying for data {my_id} in {self.dbname} for user {FeatureBroker.User}"
        )
        document = table.query(
            IndexName="idIndex", KeyConditionExpression=Key("id").eq(my_id)
        )

        logger.info("Returned from Query: %s", document)
        if document["Count"] > 0:
            converted = convert_to_dict(document["Items"][0])
            if check_user(converted, FeatureBroker.User):
                return converted
            raise ActionNotAllowed("Access to " + my_id)
        return None

    @log_time_spend("dynamo-find-item-for-review-status")
    @dynamo_exception
    def find_item_for_review_status(self, language, status, role):
        """
        Find item for review status with given attributes
        Args:
            language: Language
            status: Status
            role: Role

        Returns:
            item as dictionary or None
        """
        logger.info("Looking in %s for %s %s %s", self.dbname, language, status, role)
        table = self.get_dynamo_table()

        # TODO check on filtering based on user
        # query_data = {"idIndex": my_id}
        logger.info(
            "Querying for data in %s: %s %s %s", self.dbname, language, status, role
        )
        print(
            f"Querying for data {language} {status} {role} in {self.dbname} for user {FeatureBroker.User}"
        )
        fe = (
            Attr("language").eq(language)
            & Attr("status").eq(status)
            & Attr("role").eq(role)
        )
        document = table.scan(FilterExpression=fe)
        logger.info("Returned from Query: %s", document)
        if document["Count"] > 0:
            return convert_to_dict(document["Items"][0])
        return None

    @log_time_spend("dynamo-find-config-item")
    @dynamo_exception
    def find_config_item(self, my_id):
        """Return the item from the config database

        Args:
            my_id: id of item to be found
        Returns:
             the item in DICT format
        """
        logger.info("Looking in %s for %s", self.dbname, my_id)
        table = self.get_dynamo_table()

        logger.info("Querying for data in %s: %s", self.dbname, my_id)
        document = table.query(KeyConditionExpression=Key("config_id").eq(my_id))

        logger.info("Returned from Query: %s", document)
        if document["Count"] > 0:
            return convert_to_dict(document["Items"][0])
        return None

    def store_item(self, json_data):
        """Saves the item in the database - updates user, timestamp and ID

        Args:
            json_data: dict to be stored - will be updated
        Returns:
            updated Model
        """
        json_data["userId"] = FeatureBroker.User
        return self.share_item(json_data)

    def store_time_item(self, json_data):
        """Saves the item in the database - updates user, timestamp, but does not changes ID

        Args:
            json_data: dict to be stored - will be updated
        Returns:
            updated Model
        """
        json_data["userId"] = FeatureBroker.User
        timestamp_float = time.time()
        json_data["timestamp"] = str(round(timestamp_float * 1000))
        retention = json_data.get("retention", self.ttl_days)
        # Inject TTL (Time-to-Live) timestamp
        if self.ttl_attribute_name and retention:
            json_data[self.ttl_attribute_name] = round(
                timestamp_float + float(retention) * 24 * 3600
            )
        self.store(json_data)
        return json_data

    def share_item(self, json_data):
        """Saves the item in the database - updates user, timestamp and ID

        Args:
            json_data: dict to be stored - will be updated
        Returns:
            updated Model
        """
        timestamp_float = time.time()
        json_data["id"] = str(uuid.uuid4())
        json_data["timestamp"] = str(round(timestamp_float * 1000))
        retention = json_data.get("retention", self.ttl_days)
        # Inject TTL (Time-to-Live) timestamp
        if self.ttl_attribute_name and retention:
            json_data[self.ttl_attribute_name] = round(
                timestamp_float + float(retention) * 24 * 3600
            )
        self.store(json_data)
        return json_data

    @log_time_spend("dynamo-store-item")
    @dynamo_exception
    def store(self, json_data):
        """Saves the item in the database as is

        Args:
            json_data: dict to be stored
        """
        logger.info("Storing in %s: %s", self.dbname, json_data)
        table = self.get_dynamo_table()
        print(json.dumps({"saving": json_data}))
        table.put_item(Item=convert_to_internal(json_data))

    @log_time_spend("dynamo-update-item")
    @dynamo_exception
    def update_item(self, model, new_status):
        """
        Update item for the new status
        Args:
            model: Model
            new_status: Status to be updated

        Returns:
            item as dictionary or None
        """
        table = self.get_dynamo_table()

        print(f"Updating from user {model['userId']} at {model['status']} ")
        response = table.update_item(
            Key={"userId": model["userId"], "timestamp": model["timestamp"]},
            UpdateExpression="set #tst =:s",
            ConditionExpression=" id= :i AND userId= :u",
            ExpressionAttributeValues={
                ":s": new_status,
                ":i": model["id"],
                ":u": model["userId"],
            },
            ExpressionAttributeNames={"#tst": "status"},
            ReturnValues="UPDATED_NEW",
        )
        return response

    @dynamo_exception
    def delete_item(self, my_id):
        """Deletes the item from the database

        Args:
            my_id: id of item to be found
        Returns:
            the item in DICT format
        """
        logger.info("Deleting %s in %s", my_id, self.dbname)
        table = self.get_dynamo_table()

        # TODO check on filtering based on user
        document = table.delete_item(Key={"id": my_id})
        # TODO: Check if I need to get the default
        return convert_to_dict(document)

    @dynamo_exception
    def delete_items(self, my_key: str, sort_keys: list):
        """Deletes the item from the database

        Args:
            my_id: id of item to be found
        Returns:
            the item in DICT format
        """
        logger.info("Deleting %s - %s in %s", my_key, sort_keys, self.dbname)
        table = self.get_dynamo_table()

        # TODO check on filtering based on user
        for sort_key in sort_keys:
            document = table.delete_item(
                Key={"userId": my_key, "timestamp": sort_key},
            )
        # TODO: Check if I need to get the default
        return convert_to_dict(document)

    @log_time_spend("dynamo-get-most-recent")
    @dynamo_exception
    def get_most_recent_model(self):
        """get the most recent model for the user

        Returns:
            Dictionary containing the most recent element for each element
        """
        user_id = FeatureBroker.User
        logger.info("Getting most recent model for %s in %s", user_id, self.dbname)
        table = self.get_dynamo_table()

        document = table.query(
            KeyConditionExpression=Key("userId").eq(user_id),
            ScanIndexForward=False,
            Limit=1,
        )

        logger.info(document)
        if (
            document["ResponseMetadata"]["HTTPStatusCode"] == 200
            and "Items" in document
            and document["Items"]
        ):
            return convert_to_dict(document["Items"][0])
        raise ItemNotFound(f"model for user {user_id}")

    @log_time_spend("dynamo-get-projects")
    @dynamo_exception
    def get_projects(self, max_amount=6):
        """get list of save projects for the user - up

        args:
            max_amount: return no more than so many; to get all instances set to 0

        Returns:
            Dictionary containing the most recent element for each element
        """
        user_id = FeatureBroker.User
        logger.info("Getting list of projects for %s in %s", user_id, self.dbname)
        table = self.get_dynamo_table()

        # Only limited part is needed projectId, projectName, project,, Input, id and user_id and projectUserId
        document = table.query(
            IndexName="projectIndex",
            KeyConditionExpression=Key("projectUserId").eq(user_id),
            ScanIndexForward=False,
        )

        logger.info(document)
        if document["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise ItemNotFound(f"projects for user {user_id}")

        if not document.get("Items"):
            return []

        # We need to do two more things.
        # 1. make sure the returned projects are unique
        # 2. convert to dict, and return only limited numbers
        found_ids = set()
        projects = []
        for doc in document["Items"]:
            proj_id = doc.get("projectId")
            if not proj_id:
                print("***Missing PROJ ID:")
                print(doc)
                continue
            print(proj_id)
            if proj_id not in found_ids:
                found_ids.add(proj_id)
                # If a project is deleted - it should not show up in the list either
                # - nor any instances of the same project
                if doc.get("projectStatus") == "deleted":
                    continue
                # TODO Filter on database side to limit data transfer
                projects.append(convert_to_dict_filtered(doc, ["options", "results"]))

        if max_amount:
            return projects[0:max_amount]
        return projects

    @log_time_spend("dynamo-get-project")
    @dynamo_exception
    def get_project(self, project_id, get_deleted=False):
        """get the most recent project with the project id

        args:
            project_id: project id to look for
            get_deleted: Get deleted project also

        Returns:
            Dictionary containing the most recent element for each element
        """
        user_id = FeatureBroker.User
        logger.info("Getting list of projects for %s in %s", user_id, self.dbname)
        table = self.get_dynamo_table()

        # Only limited part is needed projectId, projectName, project, Input, id and user_id and projectUserId
        document = table.query(
            IndexName="projectIndex",
            KeyConditionExpression=Key("projectUserId").eq(FeatureBroker.User),
            ScanIndexForward=False,
        )

        print(document)
        for item in document["Items"]:
            if item.get("projectId") == project_id:
                print("------")
                print(item["projectId"])
                print(item["id"])
                print(item.get("projectStatus"))
                print(item.get("projectName"))
                print(item.get("projectUserId"))
                print(item.get("timestamp"))
                if not get_deleted and item.get("projectStatus") == "deleted":
                    # It has been deleted to technically, we cannot find it anymore
                    logger.info(
                        "Requesting deleted project with project id: %s returning 404",
                        item["projectId"],
                    )
                    raise ItemNotFound(f"project {project_id}")
                # In theory - first match should be fine since we matched time reverted
                # Currently, we have the full object here since my attempt to get only part of it failed
                # return self.find_item(item["id"])
                return convert_to_dict(item)
        raise ItemNotFound(f"project {project_id}")

    @log_time_spend("dynamo-update-retention")
    @dynamo_exception
    def update_retention_on_project(self, project_id, retention=0):
        """Mark the projects as deleted and update retention time accordingly

        args:
            project_id: project id to look for
            retention: new retention time to set

        Note that the name is misleading, It is removing this project from available saved projects and by doing so,
        updating the retention time.

        """
        if not retention:
            retention = self.ttl_days
        # TODO: Use special query for this
        user_id = FeatureBroker.User
        logger.info("Getting list of projects for %s in %s", user_id, self.dbname)
        table = self.get_dynamo_table()

        document = table.query(
            IndexName="projectIdIndex",
            KeyConditionExpression=Key("projectId").eq(project_id),
            FilterExpression=Key("userId").eq(FeatureBroker.User),
            ScanIndexForward=False,
        )
        new_retention_time = convert_to_internal(
            round(time.time() + float(retention) * 24 * 3600)
        )
        update_string = (
            f"SET {self.ttl_attribute_name} = :e REMOVE projectId, projectUserId"
        )
        for item in document["Items"]:
            print(f"Updating from user {item['userId']} at {item['timestamp']}")
            table.update_item(
                Key={"userId": item["userId"], "timestamp": item["timestamp"]},
                UpdateExpression=update_string,
                ExpressionAttributeValues={":e": new_retention_time},
            )

    def get_default_item(self):
        """Requesting default item for a particular collection

        A default item is stored as user 'default ', and the most recent is used
        The name and ID are stripped from this data as it is not meant to be updated
        Returns:
           The default items string containing the default output
        """
        raise NotImplementedError("Dynamo: get default item")

    @dynamo_exception
    def query_index(self, query_name: str, keys: List[Tuple]) -> list:
        """Return the items, or returns none if not found: keys is a list of tuples, each tuple is a key, value.
        Partition key is pos 0 in list, sort key pos 1

        Args:
            query_name: Name of the dynamodb index
            keys: list of tuples with name and value for partition key and optionally the sort key
        returns:
            The single item found

        Raises NotImplementedError for other sizes than one or two for keys
        """
        table = self.get_dynamo_table()
        if len(keys) == 2:
            query_expression = "#pk = :partitionValue AND #sk = :sortValue"
            key_names = {"#pk": keys[0][0], "#sk": keys[1][0]}
            attributes = {":partitionValue": keys[0][1], ":sortValue": keys[1][1]}
        elif len(keys) == 1:
            query_expression = "#pk = :partitionValue"
            key_names = {"#pk": keys[0][0]}
            attributes = {":partitionValue": keys[0][1]}
        else:
            raise NotImplementedError(
                "queries with more than 2 or less than 1 name, value pairs"
            )

        if query_name:
            document = table.query(
                IndexName=query_name,
                KeyConditionExpression=query_expression,
                ExpressionAttributeValues=attributes,
                ExpressionAttributeNames=key_names,
                ScanIndexForward=False,
            )
        else:
            document = table.query(
                KeyConditionExpression=query_expression,
                ExpressionAttributeValues=attributes,
                ExpressionAttributeNames=key_names,
                ScanIndexForward=False,
            )

        if (
            document["ResponseMetadata"]["HTTPStatusCode"] == 200
            and "Items" in document
            and document["Items"]
        ):
            return convert_to_dict(document["Items"])
        return []

    # ####################################
    # private methods - mostly supporting
    # ####################################

    def execute_on_each_document(self, filters, operation):
        """Execute the operation on each document found in collection using filters

        Args:
            filters: List of key value pairs to filter
            operation: Function having a document as argument that is gogin to be executed on each found document
        """
        raise NotImplementedError("Dynamo: execute_on_each_document")

    @staticmethod
    def get_dynamo_resource():
        """Gets the boto3 dynamoDB resource needed to get a table"""
        if not DynamoDB.resource_instance:
            region = os.environ.get("AWS_REGION", "eu-west-1")
            DynamoDB.resource_instance = boto3.resource("dynamodb", region_name=region)
        return DynamoDB.resource_instance

    @dynamo_exception
    def get_dynamo_table(self):
        """Gets the DynamoDB table resource. Get it from local cache if present, else create new and store in cache"""
        if self.dbname not in DynamoDB.tables:
            dynamo = DynamoDB.get_dynamo_resource()
            # pylint: disable=no-member
            table = dynamo.Table(self.dbname)
            # This is a check to see if the resource actually exists
            # Note EE: Apparently the IAM role does not posses the describe table role. Disabling this until I fix this.
            # print("Staring querying bearing table {} with {} entries".format(self.dbname, table.item_count))
            DynamoDB.tables[self.dbname] = table
        return DynamoDB.tables[self.dbname]

    def remove_dynamo_table(self):
        """Removes a table name upon error"""
        logger.warning("Removing cached table entry: %s ", self.dbname)
        if self.dbname in DynamoDB.tables:
            del DynamoDB.tables[self.dbname]
