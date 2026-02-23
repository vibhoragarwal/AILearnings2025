"""Mock database to mock modeldatabase for unit testing
"""

import logging
import time
from foundation.utils.featurebroker import FeatureBroker
from foundation.utils.customexceptions import AuthorisationError, ItemNotFound
from copy import deepcopy
from typing import Tuple, List

logger = logging.getLogger("nest.database")


class MockDatabaseModel(object):
    """Mock database class to support unit testing in an efficient manner.

    Register this class as instance.
    This class has limited functionality and in only intended for simple unit tests
    @ingroup basemodel
    """

    def __init__(self, collection):
        """Constructor

        Args:
            collection: Collection name to use for this database
            mock_id: ID that can be retrieved from the database
            default_model: model that is to be retrieved on search for mockid

        """
        ## Mimicking default database

        ## Storing of the default models
        self.default = {}
        ## Collection this instance supports
        self.collection = collection
        self.db = {}
        logger.info("Using MockDatabase for %s", collection)

    def get_user(self):
        """Get the user ID"""
        return FeatureBroker.get_if_exists("User", "test")

    def update_item_data(self, item):
        """Update all fields of an item that are under our control.
        The item can be a new creation or an full update of an existing item"""

        timestamp_float = time.time()
        item["userId"] = self.get_user()
        item["timestamp"] = str(round(timestamp_float * 1000))

        # Sequence is used to keep track of the number of updates
        # Can be used to prevent overwriting of data by parallel processes
        item["sequence"] = item.get("sequence", 0) + 1
        # Inject TTL (Time-to-Live) timestamp
        return item

    def store(self, json_data):
        """Replace Object with newData

        Args:
            json_data: data (dict) to be stored
        Returns:
             Id of stored object
        """
        if model := self.db.get(json_data["id"]):
            if model["userId"] != self.get_user():
                raise AuthorisationError(json_data["id"])

        self.db[json_data["id"]] = deepcopy(json_data)

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
        model = self.db.get(str(my_id))
        if model:
            if model["userId"] == self.get_user():
                return deepcopy(model)
            raise AuthorisationError(my_id)
        return None

    def store_item(self, json_data):
        """Stores item in database - sets time and ID

        Args:
            json_data: data (dict) to be stored
        Returns:
             Id of stored object
        """
        json_data = self.update_item_data(json_data)
        self.store(json_data)

        return json_data

    def update_item(self, model, new_status):
        """Update item for the new status - Work in progress
        Args:
            model: Model
            new_status: Status to be updated

        Returns:
            item as dictionary or None
        """

        print(f"Updating from user {model['userId']} at {model['status']} ")
        item = self.find_item(model["id"])
        if not item:
            item = {
                "id": model["id"],
                "status": new_status,
                "userId": model["userId"],
                "timestamp": model["timestamp"],
                "sequence": 1,
            }
        else:
            item["timestamp"] = model["timestamp"]
            item["status"] = new_status
            if item["userId"] != model["userId"]:
                raise AuthorisationError(model["userId"])

        self.store(item)
        return item

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
        if model := self.db.get(str(my_id)):
            if model["userId"] != self.get_user():
                raise AuthorisationError(my_id)
            del self.db[str(my_id)]

    def get_most_recent_model(self):
        """get the most recent model

        Returns:
            Dictionary containing the most recent element for each element
        """
        models = self.get_models()
        # get models throws an exception on not found
        return models[0]

    def get_models(self):
        """Get all models for the user sorted on time"""
        user = self.get_user()
        for_user = [items for items in self.db.values() if items["userId"] == user]
        for_user.sort(key=lambda x: x["timestamp"], reverse=True)
        if for_user:
            return for_user
        raise ItemNotFound(f"model for user {user}")

    # local methods

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

        def matches(instance, key_tuple):
            """return true if instance matched the keys and values requestes"""
            if key_tuple[0] not in instance or instance[key_tuple[0]] != key_tuple[1]:
                return False
            return True

        if not 1 <= len(keys) <= 2:
            raise NotImplementedError(
                "queries with more than 2 or less than 1 name, value pairs"
            )

        if not query_name:
            if len(keys) == 2:
                return [
                    deepcopy(item)
                    for item in self.db.get(keys[0][1], [])
                    if matches(item, keys[1])
                ]
            return [deepcopy(item) for item in self.db.get(keys[0][1], [])]

        parts = query_name.split("-")[:-1]
        if len(parts) not in (1, 2):
            raise AuthorisationError("Invalid index name")

        found = []
        for value in self.db.values():
            for item in value:
                if not matches(item, keys[0]):
                    continue
                if len(keys) == 2:
                    if not matches(item, keys[1]):
                        continue
                elif len(keys) == 1:
                    # Only when field in property exists, it is included in index
                    if len(parts) == 2 and parts[1] not in item:
                        continue
                found.append(deepcopy(item))
        return found
