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
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import DYNAMODB_CONTEXT
from foundation.utils.customexceptions import ActionNotAllowed, ConfigurationError
from foundation.utils.featurebroker import FeatureBroker
from foundation.utils.utils import log_time_spend

from foundation.aws_lambda.dynamodb import convert_to_internal, convert_to_dict, dynamo_exception

logger = logging.getLogger("nest.database")


def check_user(model, user):
    """ Check that loaded model user matched given user or is anonymous while user is not """
    if "userId" not in model:
        # No user in model - so there is nothing to check - that is OK by design
        return True

    if model["userId"] == user:
        return True

    # No user promotion here
    return False


class DynamoDBWorm:
    """
    Generic database wrapper for AWSs DynamoDB
    @ingroup aws_lambda
    """

    ## Cached table static resource containing tablename table mapping
    tables = {}

    def __init__(self, settings):
        """Constructor for the database
        Args:
            settings: containing the configuration options to connect to the database
        """
        ## The network configuration settings for this database
        self.settings = settings
        ## Convenience variable to contain the database name
        self.dbname = self.settings["dbname"]
        self.find_index = self.settings.get("indexName")
        self.partition_key = self.settings.get("partitionKey", "id")
        self.sort_key = self.settings.get("sortkey", "timestamp")

        ## Attribute name for (optional) item TTL (Time-to-live) expires
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
        if not self.find_index:
            document = table.query(
                KeyConditionExpression=Key(self.partition_key).eq(my_id),
                ScanIndexForward=False,
                Limit=1
            )
        else:
            document = table.query(
                IndexName=self.find_index,
                KeyConditionExpression=Key(self.partition_key).eq(my_id),
                ScanIndexForward=False,
                Limit=1,
            )

        logger.info(document)
        if document["ResponseMetadata"]["HTTPStatusCode"] == 200 and "Items" in document and document["Items"]:
            return convert_to_dict(document["Items"][0])
        return None

    @log_time_spend("dynamo-find-item")
    @dynamo_exception
    def find_items(self, my_id):
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
        dyn_table = self.get_dynamo_table()
        if not self.find_index:
            document = dyn_table.query(
                KeyConditionExpression=Key(self.partition_key).eq(my_id),
                ScanIndexForward=False
            )
        else:
            document = dyn_table.query(
                IndexName=self.find_index,
                KeyConditionExpression=Key(self.partition_key).eq(my_id),
                ScanIndexForward=False
            )

        logger.info(document)
        if document["ResponseMetadata"]["HTTPStatusCode"] == 200 and "Items" in document and document["Items"]:
            return convert_to_dict(document["Items"])
        return None


    @log_time_spend("dynamo-find-item-key")
    @dynamo_exception
    def find_item_key(self, part_key, sort_key):
        """Return the item from the database matching the partition key and the sort key
        assumes timestamp to be sort key

        Args:
            part_key: Partition key to search for
            sort_key: Sort key to search for, is usually the timestamp in WORM database

        Returns:
             the item in DICT format or None
        """
        logger.info("Looking in %s for %s %s", self.dbname, part_key, sort_key)
        table = self.get_dynamo_table()
        document = table.get_item(
            Key={self.partition_key: part_key, self.sort_key: sort_key}
        )

        logger.info(document)
        if "Item" in document and document["Item"]:
            return convert_to_dict(document["Item"])
        return None

    def store_item(self, json_data):
        """Saves the item in the database - updates user, timestamp and ID

        Args:
            json_data: dict to be stored - will be updated
        Returns:
            updated Model
        """
        current_time = time.time()  # seconds from epoch in float
        json_data["userId"] = FeatureBroker.User
        json_data["timestamp"] = str(round(current_time * 1000))
        retention = json_data.get("retention", self.ttl_days)
        # Inject TTL (Time-to-Live) expires
        if self.ttl_attribute_name and retention:
            json_data[self.ttl_attribute_name] = round(current_time + float(retention) * 24 * 3600)
        return self.store(json_data)

    @log_time_spend("dynamo-store-item")
    @dynamo_exception
    def store(self, json_data):
        """Saves the item in the database as is

        Args:
            json_data: dict to be stored
        """
        logger.info("Storing in %s: %s at %s", self.dbname, json_data[self.partition_key], json_data[self.sort_key])
        table = self.get_dynamo_table()
        print(json.dumps({"saving": json_data}))
        result = table.put_item(Item=convert_to_internal(json_data))

        # Check Results
        return json_data

    @log_time_spend("dynamo-store-item")
    @dynamo_exception
    def batch_store(self, items):
        """Saves the item in the database as is

        Args:
            json_data: dict to be stored
        """
        logger.info("Storing batch in %s: %s at %s", self.dbname)
        table = self.get_dynamo_table()
        print(json.dumps({"saving": items}))

        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=convert_to_internal(item))

        # Check Results
        return items


    @dynamo_exception
    def get_dynamo_table(self):
        """ Gets the DynamoDB table resource. Get it from local cache if present, else create new and store in cache """
        if self.dbname not in DynamoDBWorm.tables:
            dynamo = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-1"))
            # pylint: disable=no-member
            DynamoDBWorm.tables[self.dbname] = dynamo.Table(self.dbname)
        return DynamoDBWorm.tables[self.dbname]

    def remove_dynamo_table(self):
        """ Removes a table name upon error """
        logger.warning("Removing cached table entry: %s ", self.dbname)
        if self.dbname in DynamoDBWorm.tables:
            del DynamoDBWorm.tables[self.dbname]

    @dynamo_exception
    def scan_items_by_index(self, index_name: str, count: int = 0):
        """Use this method with care. Scanning is expensive operation returning large amounf of items
        and incurring high costs and probably require scaling as well
        This method is meant to be used on indeces that contain only a fraction of the data
        under development
        
        Args:
            index_name: the name of the GSI or LSI to be used
            count: Max number of items to be returned
        """
        # TODO: Use count
        logger.info("SCANNING in %s for %s - returning max amount: %i", self.dbname, index_name, count)
        limit = min(count, 1000) if count > 0 else 1000

        table = self.get_dynamo_table()
        response = table.scan(IndexName=index_name, Select="ALL_ATTRIBUTES", Limit=limit)
        items = response['Items']

        while 'LastEvaluatedKey' in response and len(items) < count:
            response = table.scan(IndexName=index_name, Select="ALL_ATTRIBUTES",
                                  ExclusiveStartKey=response['LastEvaluatedKey'], Limit=limit)
            items.extend(response['Items'])
            if 0 < count < len(items):
                items = items[:count]
                break

        return [convert_to_dict(item) for item in items]

    @log_time_spend("dynamo-find-item")
    @dynamo_exception
    def query_items(self, index_name, my_id, limit=25):
        """Return the items from the database for the current user

        Args:
            my_id: id of item to be found
        Returns:
             the item in DICT format
        """
        logger.info("Looking in %s for %s", self.dbname, my_id)
        partition_key = index_name.split("-")[0]
        table = self.get_dynamo_table()
        document = table.query(
            IndexName=index_name,
            KeyConditionExpression=Key(partition_key).eq(my_id),
            ScanIndexForward=False,
            Limit=limit,
        )

        logger.info(document)
        if document["ResponseMetadata"]["HTTPStatusCode"] == 200 and "Items" in document and document["Items"]:
            return convert_to_dict(document["Items"])
        return None

    @dynamo_exception
    def query_index(self, query_name: str, keys: List[Tuple]) -> list:
        """Return the items, or returns none if not found: keys is a list of tuples, each tuple is a key, value.
        Partition key is pos 0 in list, sort key pos 1\

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
            raise NotImplementedError("queries with more than 2 or less than 1 name, value pairs")

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

        if document["ResponseMetadata"]["HTTPStatusCode"] == 200 and "Items" in document and document["Items"]:
            return convert_to_dict(document["Items"])
        return []

    @log_time_spend("dynamo-delete-item")
    @dynamo_exception
    def delete_items(self, primary_key, sort_keys):
        """Saves the item in the database as is

        Args:
            json_data: dict to be stored
        """
        logger.info("Deleting in %s: %s at %s", self.dbname, primary_key, sort_keys)
        table = self.get_dynamo_table()
        
        with table.batch_writer() as batch:
            for sort_key in sort_keys:
                result = batch.delete_item(Key={self.partition_key: primary_key, self.sort_key: sort_key})

        print("delete result")
        print(result)

        # Check Results
        return None
    

def test_main():
    """Test Main function"""
    # table_name = "esod-simulation-simulationdb-test"
    table_name = "esod-simulation-simulationdb-jenkins-dev"
    FeatureBroker.register("User", "testUser")

    my_table = DynamoDBWorm(settings={"dbname": table_name})

    items = my_table.query_index("", [("id", "56c7765d-34b7-4377-8d6e-c6467580b6bc"), ("timestamp", "00-dashboard")])
    assert len(items) > 0
    assert items[0]["id"] == "56c7765d-34b7-4377-8d6e-c6467580b6bc"
    assert items[0]["timestamp"] == "00-dashboard"
    assert items[0]["caption"] == "Project - Finished"

    items = my_table.query_index("id-duration-index", [("id", "f3eedba1-b3bd-4e91-8c56-02b4a944206c"), ("duration", 17)])
    assert len(items) > 0
    for item in items:
        # Query index does not have to be unique
        assert item["id"] == "f3eedba1-b3bd-4e91-8c56-02b4a944206c"
        assert item["duration"] == 17
        assert item["caption"] == "Project - Finished"

    items = my_table.query_index("id-duration-index", [("id", "f3eedba1-b3bd-4e91-8c56-02b4a944206c")])
    assert len(items) > 0
    for item in items:
        # Query index does not have to be unique
        assert item["id"] == "f3eedba1-b3bd-4e91-8c56-02b4a944206c"
        assert item["duration"] == 17
        assert item["caption"] == "Project - Finished"


    items = my_table.query_items("userId-dashboard-index", "tu-d2b5c090-b9fc-4a39-a75e-8583ee6bc899")
    assert len(items) > 0
    assert items[0]["model"]
    assert items[0]["userId"]
    assert items[0]["dashboard"]


    items = my_table.scan_items_by_index("id-activated-index")
    assert len(items) > 0
    assert items[0]["activated"]
    assert items[0]["progress"]
    assert items[0]["id"]
    
    items = my_table.scan_items_by_index("id-activated-index")
    assert len(items) > 0
    assert not items[0]["queued"]
    assert items[0]["id"]

    if 0:
        item = my_table.store_item({"id": str(uuid.uuid4()), "purpose": "testing"})
        # Give it time to be distributed
        time.sleep(0.5)

        item2 = my_table.find_item(item["id"])
        item2["purpose"] = "testing: next step"

        item3 = my_table.store_item(item2)
        assert item3["id"] == item["id"]
        assert item3["timestamp"] != item["timestamp"]

        item4 = my_table.find_item(item["id"])
        assert item4 == item3


if __name__ == "__main__":
    test_main()
