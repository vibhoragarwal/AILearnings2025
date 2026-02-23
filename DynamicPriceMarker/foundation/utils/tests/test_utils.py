"""Unit test file to test the utils file inthe utils pacakge """
import json
import time
import os

import pytest

from utils.utils import (
    isclose,
    get_boolean_property,
    get_integer_property,
    create_time_uuid4,
    coded_number,
    get_boolean_value,
    load_json_file,
    merge_dicts,
    merge_dicts_remove_empty,
    get_translated_value,
    _add_to_cache,
    load_language_json_file,
    convert_dict_to_body_string,
    convert_query_string_to_dict,
    remove_null_fields_from_dict,
)

from collections import OrderedDict


def test_is_close():
    """Test if two doubles are close or not"""
    assert isclose(0.5, 0.5001, 0.001)
    assert not isclose(0.5, 0.5001, 0.00001)
    assert not isclose(0.5, 0.5001, 0.0001)
    assert isclose(1, 1.000089, 0.0001)
    assert isclose(0.50005, 0.5, 0.0001)
    assert isclose(0.0, 0.00001, abs_tol=0.0001)
    assert isclose(0.00001, 0.0, rel_tol=1)
    assert isclose(-0.5, -0.5001, 0.001)
    assert not isclose(0.5, -0.5001, 0.00001)

    assert isclose(123456.01, 123456.11, rel_tol=0.000001)

    assert not isclose(123456.01, -123465.01, rel_tol=0.000001)
    assert not isclose(12345.01, -12345.10, rel_tol=0.000001)
    assert isclose(123456, 123456, rel_tol=0.000001)
    assert isclose(1, 1, rel_tol=0.000001)
    assert isclose(1, 1.0000001, rel_tol=0.0001)
    assert not isclose(-11, -12, rel_tol=0.000001)
    assert isclose(-11, -11.0, rel_tol=0.000001)
    assert isclose(-11, -10.9999995, rel_tol=0.0001)
    assert isclose(-11, -11.0000004, rel_tol=0.0001)


def test_get_bool_property():
    """Test boolean conversion from unknown value in dictionary"""
    values = {
        "string_false": "False",
        "string_true": "true",
        "bool_true": True,
        "bool_false": False,
        "int_false": 0,
        "int_true": 1,
    }
    assert not get_boolean_property(values, "string_false")
    assert not get_boolean_property(values, "bool_false")
    assert not get_boolean_property(values, "int_false")
    assert get_boolean_property(values, "string_true")
    assert get_boolean_property(values, "bool_true")
    assert get_boolean_property(values, "int_true")


def test_get_int_property():
    """Test boolean conversion from unknown value in dictionary"""
    values = {
        "string_0": "0",
        "string_1": "1",
        "string_-1": "-1",
        "int_0": 0,
        "int_1": 1,
        "invalid_1": "No1",
        "invalid_2": "",
        "invalid_3": None
    }

    assert get_integer_property(values, "string_0") == 0
    assert get_integer_property(values, "string_1") == 1
    assert get_integer_property(values, "string_-1") == -1
    assert get_integer_property(values, "int_0") == 0
    assert get_integer_property(values, "int_1") == 1
    assert get_integer_property(values, "invalid_1") is None
    assert get_integer_property(values, "invalid_2") == 0
    assert get_integer_property(values, "invalid_2", default=1) == 1
    assert get_integer_property(values, "invalid_3") == 0
    assert get_integer_property(values, "invalid_3", default=1) == 1
    assert get_integer_property(values, "string_non_existing") == 0
    assert get_integer_property(values, "string_non_existing", default=1) == 1


def test_get_boolean_value():
    """Test boolean conversion from unknown value in dictionary"""
    assert get_boolean_value("False") is False
    assert get_boolean_value("") is False
    assert get_boolean_value(0) is False
    assert get_boolean_value(False) is False

    assert get_boolean_value("True") is True
    assert get_boolean_value("true") is True
    assert get_boolean_value(1) is True
    assert get_boolean_value(2) is True
    assert get_boolean_value(True) is True


def test_load_json_file():
    """Test loading of JSON file with few options"""

    #     def load_json_file(filename, model_name=None, pathname=None):
    with pytest.raises(FileNotFoundError):
        load_json_file("non_existing.json")

    # More to come - like test actual loading - with providing path and with setting env


def test_merge_dicts():
    """test some complex merge scenarios"""

    left = {
        "a": 1,
        "b": "2",
        "c": {
            "ca": 1,
            "cb": 2,
            "cc": {"ccd": [1, 2, 3], "cca": 1, "cce": [0, 1]},
            "cd": [{"cda": 1, "cdb": 2}, {}],
        },
    }
    right = {
        "b": "3",
        "c": {
            "ca": 3,
            "cc": {
                "ccd": [4, 5, 6, 7],
            },
            "cd": [{"cda": 3}, {"cda": 3}],
        },
        "d": [1, 2, 3],
    }
    expected = {
        "a": 1,
        "b": "3",
        "c": {
            "ca": 3,
            "cb": 2,
            "cc": {"ccd": [4, 5, 6, 7], "cca": 1, "cce": [0, 1]},
            "cd": [{"cda": 3, "cdb": 2}, {"cda": 3}],
        },
        "d": [1, 2, 3],
    }
    result = merge_dicts(left, right)

    print(json.dumps(expected, indent=2))
    print(json.dumps(result, indent=2))
    assert compare_dict(expected, result)


def test_merge_dicts_remove_empty():
    """test some complex merge scenarios"""

    left = {
        "a": 1,
        "b": "2",
        "c": {
            "ca": 1,
            "cb": 2,
            "cc": {"ccd": [1, 2, 3], "cca": 1, "cce": [0, 1]},
            "cd": [{"cda": 1, "cdb": 2}, {}],
        },
    }
    right = {
        "d": [1, 2, 3],
        "b": "3",
        "c": {"ca": 3, "cc": "", "cd": [{"cda": 3}, {"cda": 3}]},
        "a": "",
    }
    expected = {
        "b": "3",
        "c": {"ca": 3, "cb": 2, "cd": [{"cda": 3, "cdb": 2}, {"cda": 3}]},
        "d": [1, 2, 3],
    }
    result = merge_dicts_remove_empty(left, right)
    assert compare_dict(expected, result)


def test_merge_dicts_remove_empty_in_array():
    """test some complex merge scenarios"""

    left = {
        "a": 1,
        "b": "2",
        "c": {
            "ca": 1,
            "cb": 2,
            "cc": {"ccd": [1, 2, 3], "cca": 1, "cce": [0, 1]},
            "cd": [{"cda": 1, "cdb": 2}, {}],
        },
    }
    right = {
        "d": [1, 2, 3],
        "b": "3",
        "c": {"ca": 3, "cc": None, "cd": [{}, {"cda": 3}]},
        "a": "",
    }
    expected = {
        "b": "3",
        "c": {"ca": 3, "cb": 2, "cd": [{"cda": 1, "cdb": 2}, {"cda": 3}]},
        "d": [1, 2, 3],
    }
    result = merge_dicts_remove_empty(left, right)

    assert compare_dict(expected, result)
    right = {
        "d": [1, 2, 3],
        "b": "3",
        "c": {"ca": 3, "cc": None, "cd": [None, {"cda": 3}]},
        "a": "",
    }
    expected = {"b": "3", "c": {"ca": 3, "cb": 2, "cd": [{"cda": 3}]}, "d": [1, 2, 3]}
    result = merge_dicts_remove_empty(left, right)
    print(json.dumps(expected, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))
    assert compare_dict(expected, result)


def compare_dict(left, right):
    """Compares two dicts value by value recursive"""
    lkeys = left.keys()
    rkeys = right.keys()
    if len(lkeys) != len(rkeys):
        print(f"Keys mismatch: {lkeys} vs {rkeys}")
        return False
    for key in lkeys:
        if key not in rkeys:
            print(f"Missing key {key} in {rkeys} ")
            return False
    result = True
    for key in lkeys:
        if isinstance(left[key], dict):
            result = compare_dict(left[key], right[key])
        if isinstance(left[key], list):
            if len(left[key]) != len(right[key]):
                print(f"Arrays not the same size: {key} - {rkeys}")
                result = False
            if not left[key]:
                # Same size as right, but both are empty. That is OK
                continue
            if isinstance(left[key][0], dict):
                for item in zip(left[key], right[key]):
                    result = compare_dict(item[0], item[1])
                    if not result:
                        break
            else:
                for item in zip(left[key], right[key]):
                    result = item[0] == item[1]
                    if not result:
                        break
        else:
            result = left[key] == right[key]
        if not result:
            print(f"Value mismatch in key {key}: {left[key]} vs {right[key]}")
            return False
    return True


def test_merge_dicts_remove_empty_in_large_array():
    """test some complex merge scenarios"""
    start_at = time.time()
    folder = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(folder, "utils-left-1.json"), "r", encoding="utf-8") as json_input:
        left = json.load(json_input)
    with open(os.path.join(folder, "utils-expected.json"), "r", encoding="utf-8") as json_input:
        expected = json.load(json_input)
    right = {
        "input": {
            "designation": "6309",
            "loadcycles": [{"axialForce": None}],
        }
    }
    result = merge_dicts_remove_empty(left, right)

    duration = time.time() - start_at
    print(f"total duration: {duration}")
    print(json.dumps(result))
    assert compare_dict(expected, result)

    start_at = time.time()
    with open(os.path.join(folder, "utils-left-2.json"), "r", encoding="utf-8") as json_input:
        left = json.load(json_input)
    right = {
        "input": {
            "designations": [{}, "6309"],
            "loadcycles": [
                {"weight": 2},
                {"perBearing": {"outerRingTemperature": 100}},
            ],
        }
    }

    result = merge_dicts_remove_empty(left, right)

    duration = time.time() - start_at
    print(f"total duration: {duration}")
    print(json.dumps(result))


def test_translate_value_by_dict():
    """test translation using a dict as format"""
    my_dict = {"one": "een", "two": "twee", "three": "drie"}
    assert get_translated_value("two", my_dict) == "twee"
    assert get_translated_value("three", my_dict) == "drie"
    assert get_translated_value("four", my_dict) == "four"


def test_translate_value_by_list():
    """test translation using a list of dicts as format"""
    my_dict = [
        {"parameter": "one", "label": "een"},
        {"parameter": "two", "label": "twee"},
        {"parameter": "three", "label": "drie"},
    ]
    assert get_translated_value("two", my_dict) == "twee"
    assert get_translated_value("three", my_dict) == "drie"
    assert get_translated_value("four", my_dict) == "four"


def test_loading_by_cache():
    """Test iif loading file is bypassed if present in cache"""
    os.environ["ENABLE_CACHE"] = "True"
    _add_to_cache("test_translation", "default", {"yes": "ja", "no": "nee"})
    assert load_language_json_file("test_translation", "default")["yes"] == "ja"


def test_convert_dict_to_body_string():
    """Test conversion of a plain dict into a body string for an URL POST (or similar)"""
    json_dict = {"Hello": "@win", "Here": "is the world!"}
    result = convert_dict_to_body_string(json_dict)
    assert result == "Hello=%40win&Here=is+the+world%21"


def test_convert_simple_query_string():
    """Simple conversion"""
    result = convert_query_string_to_dict("unitset=metric")
    assert result["unitset"] == "metric"
    result = convert_query_string_to_dict("unitset=metric&language=NL&format=format")
    assert result["unitset"] == "metric"
    assert result["language"] == "NL"
    assert result["format"] == "format"

    # Just for testing - invalid combination in practice
    result = convert_query_string_to_dict("unitset=metric&unitset=field")
    assert "metric" in result["unitset"]
    assert "field" in result["unitset"]
    assert len(result["unitset"]) == 2


def test_convert_query_string_with_symbols():
    """Test if symbols are translated properly"""
    input_string = "Hello=%40win&Here=is+the+world%21"
    response = convert_query_string_to_dict(input_string)
    assert response == {"Hello": "@win", "Here": "is the world!"}


class DummyTimings:
    """capture method timings including for API
    args:
        namespace: Namespace to use to log output
    """

    timings = OrderedDict()

    def add(self, key, value):
        """add dummy"""
        self.timings[key] = value + 20


def test_create_time_uuid4():
    """test the decorator function log_timing"""
    assert create_time_uuid4()
    assert create_time_uuid4() != create_time_uuid4()


def test_create_time_uuid4_uppercase():
    """test the decorator function log_timing"""
    # starts with time dependent part then normal uuid4
    assert create_time_uuid4(only_uppercase=True)

    # same but i hex format
    item = create_time_uuid4(only_uppercase=True, use_hex=True)
    assert item.find("-") == -1


def test_coded_number():
    """Test Ordering of converted numbers"""

    max_items = 40
    items = [coded_number(i) for i in range(max_items)]

    for i in range(1, max_items):
        assert items[i] > items[i - 1]

    item = int(time.time())
    items = [coded_number(item + i) for i in range(max_items)]

    for i in range(1, max_items):
        assert items[i] > items[i - 1]


def test_small_coded_number():
    """Test Ordering of converted numbers"""

    max_items = 36
    items = [coded_number(i) for i in range(max_items)]

    for i in range(1, max_items):
        assert items[i] > items[i - 1]

    item = int(time.time())
    items = [coded_number(item + i) for i in range(max_items * 2)]

    for i in range(1, max_items):
        assert items[i] > items[i - 1]


def test_remove_null_fields_from_dict():
    """test translation using a list of dicts as format"""
    standard_dict = {"test1": None, "test2": "not none"}
    list_dict = [
        {"test1": None, "test2": "not none"},
        {"test1": None, "test2": "not none"},
    ]
    nested_dict = {"test1": {"test11": None}, "test2": {"test22": "not none"}}
    nested_list_dict = [{"test1": [{"test11": None}], "test2": [{"test22": "not none"}]}]

    remove_null_fields_from_dict(standard_dict)
    remove_null_fields_from_dict(list_dict)
    remove_null_fields_from_dict(nested_dict)
    remove_null_fields_from_dict(nested_list_dict)

    assert standard_dict == {"test2": "not none"}
    assert list_dict == [{"test2": "not none"}, {"test2": "not none"}]
    assert nested_dict == {"test1": {}, "test2": {"test22": "not none"}}
    assert nested_list_dict == [{"test1": [{}], "test2": [{"test22": "not none"}]}]
