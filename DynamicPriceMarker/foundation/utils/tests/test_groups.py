"""Test groups functionaility"""

import pytest
from utils.groups import Groups


def test_group_creation():
    """Test if the underscore function works, and we can set translation function"""

    groups = Groups(["first"])
    assert groups.groups

    assert "first" in groups
    assert "second" not in groups


def test_group_case():
    """Test if the underscore function works, and we can set translation function"""

    groups = Groups(["firstGroup", "SecondGroup"])
    assert groups.groups

    assert "firstGroup" in groups
    assert "secondgroup" in groups


def test_group_update_string():
    """Test if the underscore function works, and we can set translation function"""

    groups = Groups(["first"])
    assert groups.groups

    groups += "Second"
    assert "first" in groups
    assert "second" in groups


def test_group_update_list():
    """Test if the underscore function works, and we can set translation function"""

    groups = Groups(["first"])
    assert groups.groups

    groups += ["Second", "Third"]
    assert "first" in groups
    assert "second" in groups
    assert "Third" in groups


def test_group_update_invalid_type():
    """Test if the underscore function works, and we can set translation function"""

    groups = Groups(["first"])
    assert groups.groups

    with pytest.raises(TypeError):
        groups += 5


def test_group_special_internal():
    """Test if the underscore function works, and we can set translation function"""

    groups = Groups(["first"], is_internal=True)
    assert "first" in groups
    assert Groups.INTERNAL in groups
    assert Groups.REGISTERED in groups

    groups = Groups(None, is_internal=True)
    assert "first" not in groups
    assert Groups.INTERNAL in groups
    assert Groups.REGISTERED in groups


def test_group_special_registered():
    """Test if the underscore function works, and we can set translation function"""

    groups = Groups(["first"], is_registered=True)
    assert "first" in groups
    assert Groups.INTERNAL not in groups
    assert Groups.REGISTERED in groups


def test_group_special_empty():
    """Test if the underscore function works, and we can set translation function"""

    groups = Groups([], is_registered=False)
    assert "first" not in groups
    assert Groups.INTERNAL not in groups
    assert Groups.REGISTERED not in groups


def test_special_group_prefix():
    """Test is skf_ prefix is beeing recognized for internals"""
    groups = Groups(["first"], is_internal=True)
    assert "skf_second" in groups
    groups += "skf_second"
    assert "skf_second" in groups

    groups = Groups(["first"], is_registered=True)
    assert "skf_second" not in groups
    groups += "skf_second"
    assert "skf_second" in groups
