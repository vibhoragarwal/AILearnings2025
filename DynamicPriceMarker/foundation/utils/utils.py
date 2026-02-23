""" Utility functions and classes for general use

@ingroup utils
"""
import os
import json
import datetime
import logging
import uuid
import time
import math
from typing import Union
from urllib import parse
from foundation.utils.i18N_base import get_language_folder
from foundation.utils.featurebroker import FeatureBroker

logger = logging.getLogger("nest.utils")
JSON_CACHE = {}


def _add_to_cache(filename, language, item):
    """Add language to cache so we have to load it only once"""
    # pylint: disable=global-statement
    global JSON_CACHE
    if not os.environ.get("ENABLE_CACHE"):
        return
    if not JSON_CACHE:
        JSON_CACHE = {language: {filename: item}}
    elif language not in JSON_CACHE:
        JSON_CACHE[language] = {filename: item}
    else:
        JSON_CACHE[language][filename] = item


def store_in_cache(func):
    """Decorator to store parameters in cache if cache enabled

    Args:
        func: function to decorate
    Returns:
         the converted item

    @ingroup utils
    """

    def wrapper(filename, language, *args, **kwargs):
        """Perform the actual conversion
        Args:
           filename: json range to read
           language: language to read
           args: additional parameters
           kwargs: additional named parameters
        Returns:
            the converted model

        """
        if JSON_CACHE:
            item = JSON_CACHE.get(language, {}).get(filename)
            if item:
                return item

        item = func(filename, language, *args, **kwargs)
        if item:
            _add_to_cache(filename, language, item)
        return item

    return wrapper


def isclose(value1, value2, rel_tol=1.0e-9, abs_tol=0.0):
    """compare two floating point values and return if values can be considered same or not.

        Implements the Math.isclose that will appear in version 3.5
        Still need to check on NaM and inf and -inf
    Args:
        value1: value need to be compared
        value2: value need to be compared
        rel_tol: Relative tolerance compared to maximum, value
        abs_tol: Absolute tolerance

    @ingroup utils
    """
    return abs(value1 - value2) <= max(rel_tol * max(abs(value1), abs(value2)), abs_tol)


def get_boolean_property(dictionary: dict, property_name: str, default=False):
    """Get the configured boolean setting as found in the configuration

    Since input is yet unknown, we allow a few values to be false: "False", "", 0 and False
     Args:
         dictionary: collection to look for a property
        property_name: Name of property of which the boolean value is to be retrieved
        default: Value to return if parameter is not present
    Returns:
       True if value is not false or "false" or 0

    @ingroup utils
    """
    bool_property = dictionary.get(property_name, default)
    return get_boolean_value(bool_property)


def get_boolean_value(value):
    """Translate the value to boolean
    Since input is yet unknown, we allow a few values to be false: "False", "", 0 and False
     Args:
        value: Value to return if parameter is not present - can be bool, string, int
    Returns:
       True if value is not false or "false" or 0
    """
    if isinstance(value, str):
        value = value.lower() != "false" and len(value) >= 1
    elif not isinstance(value, bool):
        value = bool(value)
    return value


def remove_null_fields_from_dict(dictionary):
    """Removes all fields that are null and alters the dictionary.
    There is also support for lists and nested dicts"""
    if isinstance(dictionary, list):
        for dict_item in dictionary:
            for key in list(dict_item.keys()):
                if isinstance(dict_item[key], (dict, list)):
                    remove_null_fields_from_dict(dict_item[key])
                elif dict_item[key] is None:
                    del dict_item[key]
    else:
        for key in list(dictionary.keys()):
            if isinstance(dictionary[key], dict):
                remove_null_fields_from_dict(dictionary[key])
            elif dictionary[key] is None:
                del dictionary[key]


def get_integer_property(
    dictionary: dict,
    property_name: str,
    default: int = 0,
    error: Union[int, None] = None,
) -> Union[int, None]:
    """Get the configured integer setting as found in the configuration

    Args:
        dictionary: collection to look for a property
        property_name: Name of property of which the integer value is to be retrieved
        default: Value to return if parameter is not present
        error: return in case of error
    Returns:
       integer value or error value
    """
    int_property = dictionary.get(property_name, default)
    if int_property is None or int_property == "":
        return default
    try:
        return int(int_property)
    except ValueError:
        return error


def get_translated_value(value, model):
    """ Translate the value from translated format

    Args:
        value: value to be translated
        model: data structure containing translations. Can either be a plain dict or \
        list of dicts with parameter and labels
    Returns: translated value - or value is no match
    """
    if not model:
        return value

    if isinstance(model, list):
        return next((item["label"] for item in model if item["parameter"] == value), value)

    return model.get(value, value)

def get_translated_internal_value(value, model):
    """ Translate the value from translated format

    Args:
        value: value to be translated
        model: data structure containing translations. Can either be a plain dict or \
        list of dicts with parameter and labels
    Returns: translated value - or value is no match
    """
    if not model:
        return value

    if isinstance(model, list):
        return next((item["parameter"] for item in model if item["label"] == value), value)

    for key, translated in model.items():
        if translated == value:
            return key
    return value

@store_in_cache
def load_language_json_file(filename, language, model_name=None):
    """Load a JSON file and returns the contents as dictionary

    At this moment, only the current directory is checked and the directory
    specified by env: NEST_MODEL_DIR
    Args:
        filename: File to read - expected .18n.json in name
        language: Current language  - see also FeatureBroker.Language
        model_name: Optional: name of model file to load - should not contain _model prefix
    Returns:
        dict containing JSON file contents
    """
    if ".i18n.json" not in filename:
        filename = filename.replace(".json", ".i18n.json")
    if model_name:
        pathname = os.path.join(get_language_folder(language), "model_" + model_name)
    else:
        pathname = get_language_folder(language)

    try:
        return load_json_file(filename, model_name, pathname)
    except FileNotFoundError:
        logger.info("External file not find - using defaults: %s", filename)
        pathname = model_name

    try:
        return load_json_file(filename, model_name, pathname)
    except FileNotFoundError:
        logger.info(
            "default internal not found either - looking at last alternative: %s",
            filename,
        )
    pathname = "model_" + model_name
    return load_json_file(filename, model_name, pathname)


def load_json_file(filename, model_name=None, pathname=None):
    """Load a JSON file from and returns the contents as dictionary

    if pathname is given, that path is used;
    else the path set in environment variable NEST_MODEL_DIR is used and model_name is appended if given
    Args:
        filename: File to read
        model_name: optional name of model to append as NEST_MODEL_DIR
        pathname: optional location to search for that file
    Returns:
        dict containing JSON file contents

    @ingroup utils
    """

    if not pathname:
        model_dir = os.path.join(os.environ["NEST_MODEL_DIR"])
    elif not os.path.isabs(pathname):
        model_dir = os.path.join(os.environ["NEST_MODEL_DIR"], pathname)
    else:
        model_dir = pathname

    if model_name:
        if os.path.exists(os.path.join(model_dir, model_name, filename)):
            model_dir = os.path.join(model_dir, model_name)

    path = os.path.join(model_dir, filename)
    logger.info("Reading %s", path)

    # try a few attempts
    if not os.path.exists(path) and pathname:
        path = os.path.join(os.environ["NEST_MODEL_DIR"], filename)
    # Raises an exception when not found
    with open(path) as input_file:
        return json.load(input_file)


def merge_dicts(left, right):
    """Merge two dictionaries into one"""
    merger = MergeDictionaries()
    return merger.merge(left, right)


def merge_dicts_remove_empty(left, right):
    """Merge two dictionaries and remove empty values"""
    merger = MergeDictionariesRemoveEmpty()
    return merger.merge(left, right)


def get_test_params_from_json(filename, path):
    """Load test items from jsaon and return as tuple"""
    test_items = load_json_file(filename, pathname=path)["test_items"]
    return tuple(item.values() for item in test_items)


class MergeDictionaries:
    """Merge dictionaries from right to left"""

    def merge(self, left, right):
        """Merge two dicts into one and return that

        This means that we traverse down sub dictionaries as well as list of dicts. Vectors are copied as is, as well as
        single values

        Args:
            left: Source dict - will be overwritten in destination by right that there is a collision
            right: dict that will update
        Returns:
            merge dictionary
        """
        if right is None:
            # if both as None, return None as well
            return left
        if left is None:
            return right
        result = {}
        keys = set()
        keys.update(left.keys())
        keys.update(right.keys())
        for key in keys:
            if key in right:
                if key in left:
                    result[key] = self.copy_matching_value(left[key], right[key])
                else:
                    result[key] = right[key]
            else:
                result[key] = left[key]
        return result

    def merge_lists(self, left, right):
        """Merge two lists. This can be list of dicts or list of scalars

        list of scalars is returned right, list of dicts is merged

        Args:
            left: Source dict - will be overwritten in destination by right that there is a collision
            right: dict that will update
             merge_dicts_function: Function to use to merge dicts
        Returns:
            merge dictionary
        """

        if not len(left):
            return right
        if not isinstance(left[0], dict):
            return right

        # make new result have the length of target -
        result = []
        for i, value in enumerate(right):
            if i < len(left):
                result.append(self.merge(left[i], value))
            else:
                result.append(value)
        return result

    def copy_matching_value(self, left_value, right_value):
        """merge a value from left and right and return the result

        Args:
            left_value: Source dict - will be overwritten in destination by right that there is a collision
            right_value: dict that will update
        Returns:
            merge dictionary
        """
        if isinstance(left_value, dict) and isinstance(right_value, dict):
            return self.merge(left_value, right_value)
        if isinstance(left_value, list) and isinstance(right_value, list):
            return self.merge_lists(left_value, right_value)
        return right_value


class MergeDictionariesRemoveEmpty(MergeDictionaries):
    """Merged two dictionaries but removed empty values, ignores empty dictionaries"""

    def merge(self, left, right):
        """Merge two dicts into one and return that. If field is empty in right, it will be removed

        This means that we traverse down sub dictionaries as well as list of dicts. Vectors are copied as is, as well as
        single values

        Args:
            left: Source dict - will be overwritten in destination by right that there is a collision
            right: dict that will update
        Returns:
            merge dictionary
        """
        result = {}
        keys = set()
        left = left or {}
        right = right or {}
        keys.update(left.keys())
        keys.update(right.keys())
        for key in keys:
            if key in right:
                if right[key] is None:
                    continue
                if isinstance(right[key], str) and not right[key]:
                    continue
                if key in left:
                    result[key] = self.copy_matching_value(left[key], right[key])
                else:
                    result[key] = right[key]
            else:
                result[key] = left[key]
        return result

    def merge_lists(self, left, right):
        """Merge two lists. This can be list of dicts or list of scalars

        list of scalars is returned right, list of dicts is merged

        Args:
            left: Source dict - will be overwritten in destination by right that there is a collision
            right: dict that will update
             merge_dicts_function: Function to use to merge dicts
        Returns:
            merge dictionary
        """

        if not left:
            return right
        if not isinstance(left[0], dict):
            return right

        # make new result have the length of target -
        result = []
        for i, right_value in enumerate(right):
            if right_value is None:
                continue
            if i < len(left):
                result.append(self.merge(left[i], right_value))
            else:
                value = right_value
                if isinstance(right_value, dict):
                    value = {dict_key: dict_value for dict_key, dict_value in right_value.items() if dict_value is not None}
                result.append(value)
        return result


def convert_dict_to_body_string(body):
    """convert key: value to key=value url safe like an HTML form would send"""
    return "&".join([key + "=" + parse.quote_plus(value) for key, value in body.items()])


def convert_query_string_to_dict(query_string):
    """Convert query string in format a=b&c=d into dict

    Args:
        query_string: Query string to be parsed
    Returns:
        Dict: When a parameter contains only one value, the actual value is returned else the list

    @ingroup utils
    """
    result = parse.parse_qs(query_string)
    for name, value in result.items():
        # replace lists of len 1 with its value
        if len(value) == 1:
            result[name] = value[0]
            # result[parse.unquote(name)] = parse.unquote(value[0])
        # TODO consider not to support more than one item
    return result


def create_error_response(error_code, error_message):
    """Create a default error response with given error code and error message

    Args:
        error_code: integer value to indicate what is wrong
        error_message: message giving more information
    Returns:
         formatted string
    """
    return (
        '{"calculated": { },"status": ' + str(error_code) + ', "message": "' + error_message.replace('"', "`") + '" }'
    )


def log_time_spend(name):
    """Decorator for functions to track the time spend in decorated function

    usage as follows
     @log_spend_time("name to appear in overview")
    Args:
        name: name to be used when logging
    Returns:
         the response of the decorated function
    """

    def log_function_time(func):
        """Decorator to track the time spend in decorated function

        Args:
            func: function to decorate
        Returns:
             the response of the decorated function
        """

        def wrapper(*args, **kwargs):
            """Perform the actual conversion
            Args:
               args: additional parameters
               kwargs: additional named parameters
            Returns:
                the converted model

            """
            start_time = datetime.datetime.now()
            result = func(*args, **kwargs)
            # register feature "log_function_time" as False, to disable logging
            if FeatureBroker.is_inactive_feature_flag("log_function_time"):
                return result
            duration = datetime.datetime.now() - start_time
            milisecond = int(duration.total_seconds() * 1000)  # convert to milliseconds
            print(f"MONITORING|{milisecond}|ms|time|{name}")
            return result

        return wrapper

    return log_function_time


def create_time_uuid4(only_uppercase: bool = False, use_hex: bool = False) -> str:
    """Create a uuid based string with a time dependent prefix - usefull for ordering files

    If only_uppercase it True, then the files will be showne ordered in case insensitive ordering (like Windows, S3)
    If use_hex is true, you will get a value without '-' signes inside like ac28e4efd0ef445d819b80e796f88d13 else 2a1e6ea9-9d41-4fe6-b3cc-da66cbae9a8d

    """
    id_value = str(uuid.uuid4().hex) if use_hex else "-" + str(uuid.uuid4())
    if only_uppercase:
        return small_coded_number(int(time.time() / 1000)) + id_value
   
    return coded_number(int(time.time() / 1000)) + id_value


def coded_number(value: int) -> str:
    """Create a base62 number from an integer - usefull for sorting"""

    def int_to_char(number):
        """translate one nmumber int its char equivalent"""
        if number < 10:
            return chr(ord("0") + number)
        elif number < 36:
            return chr(ord("A") + number - 10)
        else:
            return chr(ord("a") + number - 36)

    base = 10 + 26 + 26
    digits = []
    while value:
        digits.append(int(value % base))
        value //= base
    return "".join([int_to_char(x) for x in digits[::-1]])


def small_coded_number(value: int) -> str:
    """Create a base62 number from an integer - usefull for sorting"""

    def int_to_char(number):
        """translate one nmumber into its char equivalent"""
        if number < 10:
            return chr(ord("0") + number)
        else:
            return chr(ord("A") + number - 10)

    base = 10 + 26
    digits = []
    while value:
        digits.append(int(value % base))
        value //= base
    return "".join([int_to_char(x) for x in digits[::-1]])


def compare_float_array(left_array, right_array, rel_tol=1e-9, abs_tol=0.0):
    """Compare two float arrays - and use relative differences or absolute when close to zero"""
    for left,right in zip(left_array, right_array):
        if not math.isclose(left, right, rel_tol=rel_tol, abs_tol=abs_tol):
            return False
    if len(left_array) != len(right_array):
        return False
    return True
