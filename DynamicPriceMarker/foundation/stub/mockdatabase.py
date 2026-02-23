"""Mock database to mock modeldatabase for unit testing
"""

import logging
import random
import time
from copy import deepcopy
from typing import Tuple, List

logger = logging.getLogger("nest.database")


class MockDatabase(object):
    """Mock database class to support unit testing in an efficient manner.

    Register this class as instance.
    This class has limited functionality and in only intended for simple unit tests
    @ingroup basemodel
    """

    def __init__(self, collection, mock_id=None, default_model=None):
        """Constructor

        Args:
            collection: Collection name to use for this database
            mock_id: ID that can be retrieved from the database
            default_model: model that is to be retrieved on search for mockid

        """
        ## Mimicking default database
        self.db = {}
        ## Storing of the default models
        self.default = {}
        ## Collection this instance supports
        self.collection = collection
        if mock_id or default_model:
            self.add_collection(collection, str(mock_id), default_model)
        else:
            self.db[collection] = {}
            self.default[collection] = {}
        logger.info("Using MockDatabase for %s", collection)

    # Public Interface
    def is_connected(self):
        """Returns True - Mock database is always connected"""
        return True

    def find_item(self, my_id):
        """Mimic searching for an item

        Args:
            my_id: id to search for
        Returns:
            string my object if id == mockId or None
        """
        model = self.db[self.collection].get(str(my_id))
        if model:
            return deepcopy(model)
        return None

    def find_config_item(self, my_id):
        """Mimic searching for an item

        Args:
            my_id: id to search for
        Returns:
            string my object if id == mockId or None
        """
        model = self.db[self.collection].get(str(my_id))
        if model:
            return deepcopy(model)
        return None

    def store_item(self, json_data):
        """Stores item in database - sets time and ID

        Args:
            json_data: data (dict) to be stored
        Returns:
             Id of stored object
        """
        json_data["userId"] = "test"

        # TODO: Check that this is correct. Is it not store?
        return self.share_item(json_data)

    def store_time_item(self, json_data):
        """Stored item, updates timestamp, but does not update id"""
        json_data["timestamp"] = int(round(time.time() * 1000))

        self.store(json_data)
        return json_data
        # json_data['userId'] = 'test'

    def share_item(self, json_data):
        """Store Item, but do not set user

        Args:
            json_data: data (dict) to be stored
        Returns:
             Id of stored object
        """
        json_data["timestamp"] = int(round(time.time() * 1000))
        my_id = json_data.get("id")
        if not my_id:
            my_id = str(random.randint(10000, 100000))
            while self.db[self.collection].get(my_id):
                my_id = str(random.randint(10000, 100000))
            json_data["id"] = my_id

        self.store(json_data)
        return json_data

    @staticmethod
    def find_item_for_review_status(language, status, role):
        """Find item that needs to be reviewed"""
        # logger.info("Looking in %s for %s %s %s", self.dbname, language, status, role)
        # table = self.get_dynamo_table()

        # TODO check on filtering based on user
        # query_data = {"idIndex": my_id}
        # logger.info("Querying for data in %s: %s %s %s", self.dbname, language, status, role)
        # print(
        #     "Querying for data %s %s %s in %s for user %s" % (language, status, role, self.dbname, FeatureBroker.User))
        # fe = Attr('language').eq(language) & Attr('status').eq(status) & Attr('role').eq(role)
        # document = table.scan(FilterExpression=fe)
        # logger.info("Returned from Query: %s", document)
        # if document["Count"] > 0:
        #     return convert_to_dict(document["Items"][0])
        return None

    def store(self, json_data):
        """Replace Object with newData

        Args:
            json_data: data (dict) to be stored
        Returns:
             Id of stored object
        """
        self.db[self.collection][json_data["id"]] = deepcopy(json_data)
        return json_data

    def delete_item(self, my_id):
        """Deletes a particular version in the database and returns the ID of the previous version

        Storing or updating the default item
        Should only be done when there has been a change oor if there is no default yet
        Args:
         my_id: data to be deleted?
        Returns:
         string containing the default output
        TODO: Is this correct - Please check
        """
        if not str(my_id) in self.db[self.collection]:
            # no items deleted
            return 0
        del self.db[self.collection][str(my_id)]
        # one item deleted
        return 1

    def delete_items(self, my_key: str, sort_keys: list):
        """Deletes a particular version in the database and returns the ID of the previous version

        Storing or updating the default item
        Should only be done when there has been a change oor if there is no default yet
        Args:
         my_id: data to be deleted?
        Returns:
         string containing the default output
        TODO: Is this correct - Please check
        """
        if not str(my_key) in self.db[self.collection]:
            # no items deleted
            return 0
        for time_key in sort_keys:
            found = None
            for item in self.db[self.collection]:
                if item["userId"] == my_key and item["timestamp"] == time_key:
                    found = item
            if found:
                del self.db[self.collection][str(found["id"])]
        return 1

    def get_most_recent_model(self):
        """get the most recent model

        Returns:
            Dictionary containing the most recent element for each element
        """
        for model in self.db[self.collection].values():
            return deepcopy(model)
        return None

    def get_default_item(self):
        """Simulate getting the default item from the dabasase

        by reading the default.json file as this file is also
        used to store in de database
        """
        return deepcopy(self.default[self.collection]["default"])

    # local methods

    def add_collection(self, collection, my_id, default_model):
        """Add a collection and sets the default model

        Args:
         collection:: collection to create
         my_id: ID to add
         default_model: Default data model
        """
        default_model["id"] = my_id
        model = deepcopy(default_model)
        if "timestamp" not in model:
            # For testing purposes it might be handy to fix timestamp on default model
            model["timestamp"] = int(round(time.time() * 1000))
        model["expires"] = round(model.get("retention", 14) * 24 * 3600 + time.time())
        model["userId"] = "test"
        self.db[collection] = {my_id: model}
        self.default[collection] = {}
        # Store default item without user or timestamp added
        self.store_default_item(default_model)

    def get_ids(self):
        """Get the one MockID

        Returns:
             string json with one entry
        """
        result = []
        for key, model in self.db[self.collection].items():
            result.append([{"id": key, "timestamp": model["timestamp"]}])
        return {"models": result}

    def store_default_item(self, data):
        """Storing or updating the default item

        Should only be done when there has been a change or if there is no default yet
        "id" will be removed from top level of dictionary
        Args:
         data: The new default Item
        Returns:
         string containing the default output
        """
        default = deepcopy(data)
        if "id" in default:
            del default["id"]
        self.default[self.collection]["default"] = default

    def delete_all_for_user(self):
        """Deletes all the items in the collection for the user

        Returns:
         The number of deleted items
        """
        items = len(self.db[self.collection])
        self.db[self.collection] = {}
        return items  # remove the default item from the count

    def get_usage_stats(self):
        """Mimic the get user stats per user function

        Returns:
            Json file with some made up data
        """
        return [
            {
                "name": "test",
                "count": len(self.db[self.collection]),
                "lastModified": 1516188065,
            }
        ]

    def get_projects(self, max_amount):
        """Get the projects from the database"""
        projects = [
            model
            for key, model in self.db[self.collection].items()
            if "projectUserId" in model
        ]
        found_projects = set()
        found = []
        for project in projects:
            found_projects.add(project["projectId"])
        for project in reversed(projects):
            if project["projectId"] in found_projects:
                found_projects.remove(project["projectId"])
                if project.get("projectStatus") != "deleted":
                    found.append(project)

        return deepcopy(found[:max_amount])

    def get_project(self, project_id):
        """Get the projects from the database"""
        # For mocking - no need to match user id as well
        projects = [
            model
            for key, model in self.db[self.collection].items()
            if "projectId" in model and model["projectId"] == project_id
        ]
        if projects[-1].get("projectStatus") == "deleted":
            return None
        return deepcopy(projects[-1])  # return the last element

    def update_retention_on_project(self, project_id, retention=0):
        """get the model ids from all versions of this project

        args:
            project_id: project id to look for
            retention: new retention time to set

        """
        if not retention:
            retention = 7

        projects = [
            model
            for key, model in self.db[self.collection].items()
            if "projectId" in model and model["projectId"] == project_id
        ]
        new_expired_time = round(retention * 24 * 3600 + time.time())
        for item in projects:
            item["expires"] = new_expired_time
            item["projectStatus"] = "deleted"

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

        def matches(instance):
            """return true if instance matched the keys and values requestes"""
            if not 1 <= len(keys) <= 2:
                raise NotImplementedError("For other than one or two keys")
            for key in keys:
                if key[0] not in instance or instance[key[0]] != key[1]:
                    return False
            return True

        matching_items = [
                deepcopy(item)
            for item in self.db[self.collection].values()
                if matches(item)
            ]
        return matching_items
