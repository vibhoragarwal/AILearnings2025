"""Mock database to mock modeldatabase for unit testing
"""

import logging
import bisect
import copy

import time
from foundation.utils.featurebroker import FeatureBroker
from foundation.utils.customexceptions import AuthorisationError
from copy import deepcopy
from typing import Tuple, List

logger = logging.getLogger("nest.database")


class MockDatabaseRead(object):
    """Mock database class to support unit testing in an efficient manner.

    Register this class as instance.
    This class has limited functionality and in only intended for simple unit tests
    @ingroup basemodel
    """

    def __init__(self, settings, input_data):
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
        self.settings = settings
        self.collection = settings.get("dbname", "mocked")
        self.db = {}
        self.part_key = settings.get("part_key", "id")
        self.sort_key = settings.get("sort_key", "timestamp")
        self.ttl_key = settings.get("ttl_attribute_name", "expires")
        self.ttl_days = settings.get("ttl_days", 7)
        # To check that correct queries are used, the queries need to be defined
        self.queries = settings.get("queries", {})
        self.input_data = input_data or [] # for cloning
        logger.info("Using MockDatabase for %s", self.collection)

        # Since this is a read only database - data needs to be preloaded
        self.load_database(input_data or [])

    def clone(self, settings: dict):
        """Clone the database object"""
        new_settings = {**self.settings, **settings}
        return MockDatabaseRead(new_settings, self.input_data)

    def load_database(self, input_data):
        """Load the database with the input data"""

        def get_sort_key(obj):
            return obj[self.sort_key]

        for item in input_data:
            if self.db.get(item[self.part_key]):
                index = bisect.bisect_left(
                    [get_sort_key(obj) for obj in self.db[item[self.part_key]]],
                    get_sort_key(item),
                )
                self.db[item[self.part_key]].insert(index, item)
            else:
                self.db[item[self.part_key]] = [item]

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
            if isinstance(model, list):
                return deepcopy(model[-1])
            return deepcopy(model)
        return None

    def get_item(self, my_id, sort_key):
        """Mimic searching for an item

        Args:
            my_id: id to search for
        Returns:
            string my object if id == mockId or None
        """
        model = self.db.get(str(my_id))
        if model:
            if isinstance(model, list):
                item = next(
                    (item for item in model if item[self.sort_key] == sort_key), None
                )
            else:
                item = model if model[self.sort_key] == sort_key else None
            if item:
                return deepcopy(item)
        return None

    def get_items(self, my_id):
        """Mimic searching for an item

        Args:
            my_id: id to search for
        Returns:
            string my object if id == mockId or None
        """
        model = self.db.get(str(my_id))
        if model:
            if isinstance(model, list):
                # reverse lift as list is sorted in ascending order
                return deepcopy(model[::-1])
            else:
                return deepcopy([model])
        return None

    # local methods
    def query_index(
        self, query_name: str, keys: List[Tuple], sort_compare: str = None, max_items=0
    ) -> list:
        """Return the items, or returns none if not found: keys is a list of tuples, each tuple is a key, value.
        Partition key is pos 0 in list, sort key pos 1

        Args:
            query_name: Name of the dynamodb index
            keys: list of tuples with name and value for partition key and optionally the sort key
            sort_compare: one fo the following strings: =, <, <=, >=, >, begins_with; = is default
            max_items: max number of items returned
        returns:
            The single item found

        Raises NotImplementedError for other sizes than one or two for keys
        """

        def compare_sort_key(item, sort_key, value):
            """Compare on the sort key"""
            if sort_key not in item:
                return False
            match sort_compare:
                case "=":
                    return item[sort_key] == value
                case "<":
                    return item[sort_key] < value
                case "<=":
                    return item[sort_key] <= value
                case ">=":
                    return item[sort_key] >= value
                case ">":
                    return item[sort_key] > value
                case "begins_with":
                    return item[sort_key].startswith(value)

        def matches(instance):
            """return true if instance matched the keys and values requestes"""
            if keys[0][0] not in instance or instance[keys[0][0]] != keys[0][1]:
                return False
            return True

        if not 1 <= len(keys) <= 2:
            raise NotImplementedError("For other than one or two keys")

        if not query_name:
            if len(keys) == 2:
                return [
                    deepcopy(item)
                    for item in self.db.get(keys[0][1], [])
                    if compare_sort_key(item, keys[1][0], keys[1][1])
                ]
            return [deepcopy(item) for item in self.db.get(keys[0][1], [])]

        # Lookup quieries in query list, but use index splitting as legacy fallback
        parts = self.queries.get(query_name, query_name.split("-")[:-1])
        if len(parts) not in (1, 2):
            raise AuthorisationError("Invalid index name")

        found = []
        for value in self.db.values():
            for item in value:
                if not matches(item):
                    continue
                if len(keys) == 2:
                    if not compare_sort_key(item, keys[1][0], keys[1][1]):
                        continue
                elif len(keys) == 1:
                    # Only when field in property exists, it is included in index
                    if len(parts) == 2 and parts[1] not in item:
                        continue
                found.append(deepcopy(item))
        return found[:max_items] if max_items else found

    def delete_item(self, my_id, sort_key=None):
        """Mimic deleting an item

        Args:
            my_id: id to search for
        Returns:
            string my object if id == mockId or None
        """
        model = self.db.get(str(my_id))
        if not model:
            return None

        # model is always a list
        # TODO: Check behaviour when no sort key as argument but specified in table
        # Delete then all items with same partition key? What does DDB do?
        
        if self.sort_key:
            item = next(
                (item for item in model if item[self.sort_key] == sort_key),
                None,
            )
            if item:
                model.remove(item)
        else:
            # Need to check the behaviour in DYnamoDB on this
            del self.db[str(my_id)]

    def put_item(self, item, set_ttl=True):
        """Mimic putting an item

        Args:
            item: item to put
        Returns:
            string my object if id == mockId or None
        """
        if set_ttl and self.ttl_days > 0:
            item[self.ttl_key] = int(time.time()) + 86400 * self.ttl_days

        if model := self.db.get(item[self.part_key]):
            if self.sort_key:
                index = bisect.bisect_left(
                    [obj[self.sort_key] for obj in model],
                    item[self.sort_key],
                )
                if index < len(model) and model[index][self.sort_key] == item[self.sort_key]:
                    # Replace the existing item
                    model[index] = deepcopy(item)
                else:
                    # Insert the new item at the correct position
                    self.db[item[self.part_key]].insert(index, deepcopy(item))
            else:
                # No sort key - replace the item
                self.db[item[self.part_key]] = [deepcopy(item)]
        else:
            self.db[item[self.part_key]] = [deepcopy(item)]

    def put_batch_items(self, items, set_ttl=True):
        """Add all itmes to the database"""
        for item in items:
            self.put_item(item, set_ttl)

    def scan_index(self, index_name, max_items=0):
        """Get all items that contain a property mentioned in the index name"""

        parts = index_name.split("-")
        if len(parts) not in (2, 3):
            raise AuthorisationError("Invalid index name")

        found = []
        attributes = parts[:-1]
        for value in self.db.values():
            for item in value:
                if all(at in item for at in attributes):
                    found.append(deepcopy(item))
        return found[:max_items] if max_items else found

    def update_item(self, item: dict, updates: dict):
        """Updating items as given in updates"""

        item = copy.deepcopy(item)
        if self.sort_key:
            found = self.get_item(item[self.part_key], item[self.sort_key])
            # Inline with dynamo: If not exists, create a new item
            if not found:
                found = {self.part_key: item[self.part_key], self.sort_key: item[self.sort_key]}            
        else:
            found = self.find_item(item[self.part_key])
            if not found:
                found = {self.part_key: item[self.part_key]}

        if set_fields := updates.get("SET"):
            for field in set_fields:
                found[field]=item[field]
        if remove_fields := updates.get("REMOVE"):
            for field in remove_fields:
                if field in found:
                    del found[field]
                if field in item:
                    del item[field]
        if add_fields := updates.get("ADD"):
            for field in add_fields:
                found[field] = item[field] if field not in found else found[field] + item[field]
                item[field] = found[field]
        self.put_item(found)

        # Return the updated item not the stored item
        return item
