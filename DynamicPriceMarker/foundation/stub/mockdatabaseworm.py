"""Mock database to mimick Worm (Write Once Read Many times) database for unit testing
"""

import logging
import os
import json
import time
import glob
from typing import Tuple, List
from copy import deepcopy
from json.decoder import JSONDecodeError
from foundation.utils.docker_support import (
    get_list_of_files,
    copy_file_from_container,
    copy_file_to_container,
)
from foundation.utils.featurebroker import FeatureBroker

logger = logging.getLogger("nest.database")


class MockDatabaseWorm:
    """Mock database class to support unit testing in an efficient manner.

    Register this class as instance.
    This class has limited functionality and in only intended for simple unit tests
    @ingroup basemodel
    """

    def __init__(self, settings):
        """Constructor

        Args:
            settings: settings for this class

        """
        ## Mimicking default database
        self.db = {}

        ## Collection this instance supports
        self.collection = settings.get("collection", "default")
        self.container_id = settings.get("container_id", "")
        self.path = settings.get("path", "")
        self.add_collection(self.collection)
        if self.path:
            os.makedirs(self.path, exist_ok=True)
        logger.info("Using MockDatabase for %s", self.collection)

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
        if not self.path:
            model = self.db[self.collection].get(str(my_id))
            if model:
                # Sort to get one with highest number - when using sort key
                model = sorted(
                    model, key=lambda item: item.get("timestamp", "0"), reverse=True
                )
                return deepcopy(model[0])
            return None

        return self.get_stored_model(my_id)

    def find_item_key(self, part_key, sort_key):
        """Mimic searching for an item matching both partiotion key and and sort key

        Args:
            part_key: id to search for
            sort_key: Sort key to search for, is usually the timestamp in a worm database
        Returns:
            string my object or None
        """
        if not self.path:
            model = self.db[self.collection].get(str(part_key))
            if model:
                # Sort to get one with highest number - when using sort key
                found = next(
                    (item for item in model if item["timestamp"] == sort_key), None
                )
                if found:
                    return deepcopy(found)
            return None

        return self.get_stored_model_by_key(part_key, sort_key)

    def store_item(self, json_data):
        """Replace Object with newData

        Args:
            json_data: data (dict) to be stored
        Returns:
             Id of stored object
        """
        json_data["userId"] = FeatureBroker.get_if_exists("User", "test")
        json_data["timestamp"] = str(int(time.time() * 1000))

        return self.store(json_data)

    # Not API function
    def store(self, json_data):
        """Replace Object with newData

        Args:
            json_data: data (dict) to be stored
        Returns:
             Id of stored object
        """

        my_id = json_data["id"]
        if my_id not in self.db[self.collection]:
            self.db[self.collection][my_id] = []
        else:
            for item in self.db[self.collection][my_id]:
                if item["timestamp"] == json_data["timestamp"]:
                    # THere can be only one
                    self.db[self.collection][my_id].remove(item)
                    break

        self.db[self.collection][my_id].append(deepcopy(json_data))

        if self.path:
            filename = os.path.join(
                self.path, f"{json_data['id']}-{json_data['timestamp']}"
            )
            with open(filename, "w") as json_output:
                json.dump(json_data, json_output)

            if self.container_id:
                copy_file_to_container(container_id=self.container_id, path=filename)

        return deepcopy(self.db[self.collection][my_id][-1])

    def add_collection(self, collection):
        """Add a collection and sets the default model

        Args:
         collection:: collection to create
        """
        if collection not in self.db:
            self.db[collection] = {}

    def update_from_container(self, search_id):
        """Sync files in docker to my local folder"""
        # First sync with remote files
        files = get_list_of_files(self.container_id, self.path)
        for i in files:
            path = os.path.join(self.path, i)
            if search_id and search_id in path:
                # Unfortunately, this database is for sometimes also used for uptates
                copy_file_from_container(path, self.container_id)

    def get_stored_model(self, my_id):
        """Get the latest stored item that starts with the id"""

        if self.container_id:
            self.update_from_container(my_id)

        pathname = os.path.join(self.path, my_id + "*")
        files = sorted(glob.glob(pathname))
        if not files:
            return None

        # now load the most recent one
        files.sort(reverse=True)
        with open(files[0], "r") as json_input:
            return json.load(json_input)

    def get_stored_models(self, my_id):
        """Get the latest stored item that starts with the id"""

        if self.container_id:
            self.update_from_container(my_id)

        pathname = os.path.join(self.path, my_id + "*")
        files = sorted(glob.glob(pathname))
        if not files:
            return None

        # now load the most recent one
        files.sort(reverse=True)
        items = []
        for item in files:
            with open(item, "r") as json_input:
                items.append(json.load(json_input))
        return items


    def get_stored_model_by_key(self, part_key, sort_key):
        """Get the latest stored item that starts with the id"""

        if self.container_id:
            # First sync with remote files
            files = get_list_of_files(self.container_id, self.path)
            for i in files:
                path = os.path.join(self.path, i)
                if part_key in i and not os.path.exists(path):
                    copy_file_from_container(path, self.container_id)

        pathname = os.path.join(self.path, f"{part_key}-{sort_key}")
        if not os.path.exists(pathname):
            return None
        with open(pathname, "r") as json_input:
            return json.load(json_input)

    def scan_items_by_index(self, index_name: str, count: int = 0):
        """Scan all items based on index name, Index-name is expected to have form or <primaryKey>-<sortkey>-index"""
        # TODO Make more generic
        parts = index_name.split("-")
        if parts[-1] == "index":
            parts = parts[:-1]
        # return a copy for each item that has all items in index-name
        return [
            deepcopy(item)
            for items in self.db[self.collection].values()
            for item in items
            if all(name in item for name in parts)
        ]

    def query_items(self, index_name, my_id, limit=25):
        """Query all items based on index name and return only the first limit items"""
        parts = index_name.split("-")
        if parts[-1] == "index":
            parts = parts[:-1]
        key = parts[0]

        # return a copy for each item that has all items in index-name
        matching = [
            deepcopy(item)
            for items in self.db[self.collection].values()
            for item in items
            if all(name in item for name in parts) and item[key] == my_id
        ]
        return matching[:limit]

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

        if not self.path:
            matching = [
                deepcopy(item)
                for items in self.db[self.collection].values()
                for item in items
                if matches(item)
            ]
        else:
            if self.container_id:
                self.update_from_container(keys[0][1] if not query_name else None)
            matching = self.get_matching_from_path(query_name, keys)
        return matching

    def get_matching_from_path(self, query_name: str, keys: List[Tuple]) -> list:
        """Return the items, or returns none if not found: keys is a list of tuples, each tuple is a key, value.
        Partition key is pos 0 in list, sort key pos 1

        Args:
            query_name: Name of the dynamodb index
            keys: list of tuples with name and value for partition key and optionally the sort key
        returns:
            The single item found

        Raises NotImplementedError for other sizes than one or two for keys
        """

        def get_partition_key():
            """get partition key ID from keys
            do not expect id key-value to be missing
            Returns:
                partition key (value of id field)
            """
            for item in keys:
                if item[0] == "id":
                    return item[1]
            return None

        def matches(instance):
            """return true if instance matched the keys and values requestes"""
            if not 1 <= len(keys) <= 2:
                raise NotImplementedError("For other than one or two keys")
            for key in keys:
                if key[0] not in instance or instance[key[0]] != key[1]:
                    return False
            return True

        matching = []
        partition_key = get_partition_key()
        # print(f'reading matching files at {self.path} for partition key {partition_key}')

        # Very inefficient, but suffices for now
        for filename in sorted(glob.glob(self.path + "/*")):
            # expect the partition key to be in file name
            # but file name could have additional suffixes such as "00-dashboard"
            if os.path.isdir(filename) or partition_key not in filename:
                continue
            with open(filename, "r") as json_data:
                try:
                    contents = json.load(json_data)
                except JSONDecodeError:
                    print(f"non json file matching {filename} skipped")
                    continue
            if matches(contents):
                matching.append(contents)

        matching = sorted(
            matching, key=lambda item: item.get("timestamp", "0"), reverse=True
        )
        return matching

    def delete_items(self, primary_key, sort_keys):
        """Saves the item in the database as is

        Args:
            json_data: dict to be stored
        """
        if primary_key not in self.db[self.collection]:
            return

        items = self.db[self.collection][primary_key]
        filtered = [item for item in items if item["timestamp"] not in sort_keys]
        self.db[self.collection][primary_key] = filtered

    # Not API function
    def batch_store(self, json_data: list):
        """Replace Object with newData

        Args:
            json_data: data (dict) to be stored
        Returns:
             Id of stored object
        """

        for item in json_data:
            self.store(item)

    def find_items(self, my_id):
        """Mimic searching for an item

        Args:
            my_id: id to search for
        Returns:
            string my object if id == mockId or None
        """
        if not self.path:
            model = self.db[self.collection].get(str(my_id))
            if model:
                # Sort to get one with highest number - when using sort key
                model = sorted(
                    model, key=lambda item: item.get("timestamp", "0"), reverse=True
                )
                return deepcopy(model)
            return None

        return self.get_stored_models(my_id)


if __name__ == "__main__":

    # worm = MockDatabaseWorm({"collection": "test", "container_id": "021bdbbfcabf", "path": "/tmp/dynamodb"})
    worm = MockDatabaseWorm({"collection": "test", "path": "/tmp/dynamodb"})

    worm.store_item({"id": "test1", "purpose": "testing"})
    worm.find_item("test1")
    assert len(worm.scan_items_by_index("id-index", 0)) > 0
