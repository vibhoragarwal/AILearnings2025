"""Test functionality for Feature Broker. Test a few common scenarios"""

import pytest
from utils.featurebroker import FeatureBroker, register_function, register_class


class Component(object):
    """Symbolic base class for components"""

    # Keep the pass to make explicit that this is ment like this
    # pylint: disable=unnecessary-pass
    pass


class MyTestItem(Component):
    """Simple test component to support testing"""

    # pylint: disable=too-few-public-methods
    def __init__(self):
        """Initializer initializes dummy value"""
        # Some dummy variable for testing
        self.a_var = 0

    def test_call(self):
        """Test call to increase dummy value"""
        self.a_var += 1


def test_singleton():
    """Test handling singleton"""
    fb1 = FeatureBroker(False)
    allow_replace = fb1.allow_replace
    fb2 = FeatureBroker(not allow_replace)

    assert fb1 is fb2
    assert fb1.allow_replace == allow_replace
    assert fb2.allow_replace == allow_replace


def test_register_provide():
    """simple function"""
    x = False

    def my_test():
        nonlocal x
        x = True

    FeatureBroker.register_function("test1", my_test)
    fb1 = FeatureBroker(False)
    assert not x
    func = fb1["test1"]
    assert not x
    func()
    assert x
    x = False
    fb1["test1"]()
    assert x
    x = False

    fb2 = FeatureBroker(True)
    fb2["test1"]()
    assert x


def test_with_args():
    """Check Registration of function"""
    x = False

    def my_test_2(y1, y2):
        nonlocal x
        x = y1 + y2

    FeatureBroker.register_function("test2", my_test_2)
    func = FeatureBroker.get("test2")
    func(3, y2=4)
    assert x == 7


def test_register_with_args():
    """Check registration with args"""
    fb1 = FeatureBroker(False)
    fb1.provide("test3", MyTestItem())
    fb1["test3"].test_call()
    assert fb1["test3"].a_var == 1
    fb1["test3"].test_call()
    assert fb1["test3"].a_var == 2


def test_class_direct_access():
    """Check Register class"""
    FeatureBroker.register("test4", MyTestItem)
    FeatureBroker.test4.test_call()

    # Used class not instance to register
    # so every call the values are reset
    # New instance on every occurrence
    assert FeatureBroker.test4.a_var == 0


def test_instance_direct_access():
    """Check instance access"""
    fb1 = FeatureBroker(False)
    fb1.provide("test5", MyTestItem())
    # instance is stored, state is kept
    fb1.test5.test_call()
    assert FeatureBroker.test5.a_var == 1


def test_as_string():
    """Check String access"""
    FeatureBroker.register("test6", "my_test")
    # Test storing a string
    assert FeatureBroker.get("test6") == "my_test"


def test_register_empty_dict():
    """Check String access"""
    FeatureBroker.register("test6b", {})

    assert FeatureBroker.get("test6b") == {}
    assert FeatureBroker.test6b == {}
    # Test storing a string
    FeatureBroker.test6b["Hello"] = "World"
    assert FeatureBroker.test6b["Hello"] == "World"


def test_function_register():
    """Check Register function in feature broker"""
    x = 0
    # pylint: disable=unused-variable

    @register_function("test7")
    def update_function():
        """Check calling function"""
        nonlocal x
        x += 1
        assert FeatureBroker.test5.a_var == 1

    FeatureBroker.test7()
    assert x == 1


def test_presence_with_hasattr():
    """Check presence of function"""
    assert not hasattr(FeatureBroker, "test8b")
    with pytest.raises(AttributeError):
        # pylint: disable=pointless-statement
        FeatureBroker.test8b

    FeatureBroker.register_function("test8b", "Hello, World")
    assert hasattr(FeatureBroker, "test8b")
    assert FeatureBroker.test8b

def test_class_register():
    """Check Register class in feature broker"""
    x = 0

    # pylint: disable=too-few-public-methods,unused-variable
    @register_class("test8")
    class TestClass:
        """Check calling function"""

        def __init__(self):
            """Initializer"""
            self.x = 2

        def print_x(self):
            """Some function to test some code"""
            nonlocal x
            x += self.x
            self.x += 1

    FeatureBroker.test8.print_x()
    assert x == 2
    FeatureBroker.test8.print_x()
    assert x == 4


def test_feature_flags():
    """Check calling function"""
    # Note FeatureBroker is global so other data mauy be present as well
    FeatureBroker.register_feature_flag("featureA", True)
    FeatureBroker.register_feature_flag("featureB", False)

    assert FeatureBroker.has_feature_flag("featureA")
    assert FeatureBroker.has_feature_flag("featureB")
    assert not FeatureBroker.has_feature_flag("featureC")

    assert FeatureBroker.is_active_feature_flag("featureA")
    assert not FeatureBroker.is_active_feature_flag("featureB")
    assert not FeatureBroker.is_active_feature_flag("featureC")

    assert not FeatureBroker.is_inactive_feature_flag("featureA")
    assert FeatureBroker.is_inactive_feature_flag("featureB")
    assert not FeatureBroker.is_inactive_feature_flag("featureC")

    found = FeatureBroker.get_feature_flags()
    # order is undetermined
    for key in ["featureA", "featureB"]:
        assert key in found
    assert "featureC" not in found
    found = FeatureBroker.get_active_feature_flags()
    assert "featureA" in found
    assert "featureB" not in found

    FeatureBroker.unregister_feature_flag("featureB")
    assert FeatureBroker.has_feature_flag("featureA")
    assert not FeatureBroker.has_feature_flag("featureB")
    assert not FeatureBroker.has_feature_flag("featureC")

    # Change the value of existing feature flag
    FeatureBroker.register_feature_flag("featureA", False)
    assert not FeatureBroker.is_active_feature_flag("featureA")


def test_as_integer():
    """Check String access"""
    FeatureBroker.register("Test12", 3)
    # Test storing a integer and check comparing
    assert 4 > FeatureBroker.Test12 > 2


def test_empty_item():
    """Check String access"""
    FeatureBroker.register("Test13", None)
    # Test storing a integer and check comparing
    assert FeatureBroker.Test13 is None

    with pytest.raises(AttributeError):
       assert FeatureBroker.Test13acb is None
