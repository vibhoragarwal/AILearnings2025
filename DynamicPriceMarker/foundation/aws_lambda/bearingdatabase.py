"""
 Bearing database: Class to assist in reading bearings from dynamo bearing database

 This file assumes that there is:
 - Env  setting (NEST_BEARING_DB_NAME) with bearing database configured
 - Dynamo table with the bearing databae in it. For now no filtering - there is only one function
 - get by id which gets the bearings by designation only.

@ingroup aws_lambda
"""

import copy
import os
import json
import logging
import boto3
import time
from botocore.exceptions import ClientError
from foundation.aws_lambda.dynamodb import convert_to_dict
from foundation.utils.customexceptions import ItemNotFound, ConfigurationError, ActionNotAllowed
from foundation.utils.utils import log_time_spend
from foundation.utils.featurebroker import FeatureBroker
from foundation.utils.i18N_base import _, translate

logger = logging.getLogger("nest.database")


def log_bearing_download(designation):
    """Log to cloudwatch the downloading of the bearing"""
    log_data = {
        "metric_name": "bearing_download",
        "namespace": "Analytics",
        "value": 1,
        "unit": "Count",
        "dimensions": {
            "user_id": FeatureBroker.User,
            "designation": designation,
        },
    }
    print(json.dumps(log_data))


CACHE = {}
MAX_CACHE_SIZE = 100


def cache_items(func):
    """Decorator to convert the function results to external

    Build a simple cache for Find Item functionality
    Args:
        func: function to decorate
    Returns:
         the converted item

    @ingroup basemodel
    """

    def wrapper(self, my_id, *args, **kwargs):
        """Perform the actual conversion
        Args:
           self: base_model class
           args: additional parameters
           kwargs: additional named parameters
        Returns:
            the converted model

        """
        if os.environ.get("NEST_BEARINGDB_CACHE", "false").lower() == "false":
            return func(self, my_id, *args, **kwargs)
        if my_id in CACHE:
            item = CACHE[my_id]
            item["last"] = time.time()
            return copy.deepcopy(item["bearing"])
        item = func(self, my_id, *args, **kwargs)
        if item:
            CACHE[my_id] = {"last": time.time(), "bearing": copy.deepcopy(item)}
            if len(CACHE) > MAX_CACHE_SIZE:
                logger.warning("Bearing Cache limit reached - clearing oldest element")
                oldest_value = None
                for key, value in CACHE.items():
                    if not oldest_value or oldest_value["last"] > value["last"]:
                        oldest_value = value
                        oldest_key = key
                CACHE.pop(oldest_key)
        return item

    return wrapper


# pylint: disable=too-few-public-methods
class BearingDatabase:
    """
    Bearing Database Wrapper. Use to retrieve one specific bearing from the bearing database in  dynamodb.
    The bearing database is configured using env variable NEST_BEARING_DB_NAME

    @ingroup aws_lambda
    """

    ## Cached table static resource containing tablename table mapping
    tables = {}

    # Note that we an build an easy bearing cache here as long as we invalidate items after a while

    def __init__(self, config):
        """Constructor for the database - registered as class - so default constructor

        args:
            config: dict Configuration dict. Should contain dbname if not default env is used
        """
        # Note EE: This should not be here
        # program should fail if account not set up correctly
        if "AWS_REGION" not in os.environ:
            logger.warning(
                "Missing AWS_REGION - Setting to default (in bearingdatabase.py)"
            )
            os.environ["AWS_REGION"] = "eu-west-1"

        ## Database name to use - config overrules environment
        config = config or {}
        print("Initializing bearing database ... config:", config)

        if os.environ.get("NEST_BEARINGDB_CACHE", "false").lower() == "false":
            print("Bearing Cache Disabled")  # See cache_items decorator

        self.log_not_found = config.get("logNotFound", True)
        self.dbname = os.environ.get("NEST_BEARING_DB_NAME")
        if config:
            if not self.dbname:
                logger.warning(
                    f"No Environment set for bearing database - using config value: {config.get('dbname', self.dbname)}"
                )
                self.dbname = config.get("dbname", self.dbname)
        if not self.dbname:
            logger.warning(
                "No configuration found for bearing database - reverting to default:"
            )
            self.dbname = "esod-bearingdb-dev"
        self.partition_key = config.get("partitionKey", "designation")
        logger.info(
            f"Initializing bearing database with {self.dbname} with config {config}"
        )

    @log_time_spend("bearingdb-find-item")
    @cache_items
    def find_item(self, my_id):
        """Return the item from the database
        Args:
         my_id: id of item to be found
        Returns:
         the item in dict format
        Raises ItemNotFound if bearing no found
        """
        log_bearing_download(my_id)
        table = self.get_dynamo_table()

        try:
            document = table.get_item(Key={self.partition_key: my_id})
        except ClientError as client_error:
            if client_error.response["Error"]["Code"] == "ResourceNotFoundException":
                print("Table not found: {}")
                print(os.environ.get("* AWS_SECRET_ACCESS_KEY", "no access key"))
                print(os.environ.get("* AWS_DEFAULT_PROFILE", "no default profile"))
                self.remove_dynamo_table()
                raise ConfigurationError(self.dbname, "Resource not found")
            if client_error.response["Error"]["Code"] == "ExpiredToken":
                print(
                    "Token expired - please renew you access credentials: {}".format(
                        client_error.response["Error"]["Message"]
                    )
                )
                raise ActionNotAllowed("Expired token. Please renew your token")
            raise

        print("MONITORING|my_id||bearing|dynamo")
        if document["ResponseMetadata"]["HTTPStatusCode"] == 200 and "Item" in document:
            return convert_to_dict(document["Item"])

        if document["ResponseMetadata"]["HTTPStatusCode"] > 299:
            logger.error(
                "error condition %s while searching for %s",
                document["ResponseMetadata"]["HTTPStatusCode"],
                my_id,
            )
            raise ConfigurationError(
                self.dbname,
                "Resource not sucessfully queried = Is configuration correct?",
            )
        if self.log_not_found:
            logger.warning("Bearing not found: %s", my_id)

        error_msg = translate(
                _("The selected designation {} is not supported by this service")
        ).format(my_id)
        raise ItemNotFound(my_id, error_msg, log_error=self.log_not_found)

    def get_dynamo_table(self):
        """Gets the DynamoDB table resource. Get it from local cache if present, else create new and store in cache"""
        if self.dbname not in BearingDatabase.tables:
            logger.info(f"Initializing boto3 database with {self.dbname}")
            dynamo = boto3.resource(
                "dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-1")
            )
            table = dynamo.Table(self.dbname)
            if table:
                try:
                    pass
                    # This is a check to see if the resource actually exists
                    # I don't have access to describe table - so disabled this check for now
                    # print("Staring querying bearing table {} with {} entries".format(self.dbname, table.item_count))
                except ClientError as client_error:
                    if (
                        client_error.response["Error"]["Code"]
                        == "ResourceNotFoundException"
                    ):
                        print(
                            f"Table not found: {self.dbname}. Are you running on the right environment?"
                        )
                        print(
                            os.environ.get("* AWS_SECRET_ACCESS_KEY", "no access key")
                        )
                        print(
                            os.environ.get(
                                "* AWS_DEFAULT_PROFILE", "no default profile"
                            )
                        )
                        raise ConfigurationError(self.dbname, "Resource not found")
                    if client_error.response["Error"]["Code"] == "ExpiredToken":
                        print(
                            f"Token expired - please renew you access credentials: {client_error.response['Error']['Message']}"
                        )
                        raise ActionNotAllowed("Expired token. Please renew your token")
                    raise
                BearingDatabase.tables[self.dbname] = table
        return BearingDatabase.tables[self.dbname]

    def remove_dynamo_table(self):
        """Removes a table name upon error, so its recreated next time"""
        logger.warning("Removing cached table entry: %s", self.dbname)
        if self.dbname in BearingDatabase.tables:
            del BearingDatabase.tables[self.dbname]
