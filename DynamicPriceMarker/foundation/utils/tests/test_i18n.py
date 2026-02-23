"""@package model_support/Utils

This file test the language files

"""
import os
from utils.i18N_base import _, Lang, translate, get_language_label, get_language_folder, get_link_for_message, \
    get_options_for_message


def test_underscore_function():
    """ Test if the underscore function works, and we can set translation function """
    my_text = _("This text should be translated")
    assert my_text == "This text should be translated"

    Lang.gettext = Dutch.gettext

    my_text = translate(my_text)
    assert my_text == "Deze text zou vertaald moeten zijn"


class Dutch:
    """ Used to test translation module. Can only translate one sentence """
    # pylint: disable=too-few-public-methods
    @staticmethod
    def fixed_message(_message):
        """A fixed Dutch message to compare"""
        assert _message == "This text should be translated"
        return "Deze text zou vertaald moeten zijn"

    gettext = fixed_message


def test_get_language_label():
    """ Test labels of languages """
    assert get_language_label("german") == "de.UTF-8"
    assert get_language_label("english") == "en_GB.UTF-8"
    assert get_language_label("default") == "en_GB.UTF-8"
    assert get_language_label("italian") == "it.UTF-8"
    assert get_language_label("dutch") == "en_GB.UTF-8"
    assert get_language_label("spanish") == "es.UTF-8"
    assert get_language_label("french") == "fr.UTF-8"
    assert get_language_label("portuguese") == "pt.UTF-8"
    assert get_language_label("chinese") == "zh.UTF-8"
    assert get_language_label("japanese") == "ja.UTF-8"
    assert get_language_label("korean") == "ko.UTF-8"
    assert get_language_label("swedish") == "sv.UTF-8"


def test_get_language_dir():
    """ Test labels of languages """
    if "NEST_MODEL_DIR" not in os.environ:
        os.environ["NEST_MODEL_DIR"] = '.'
    path = os.path.join(os.environ["NEST_MODEL_DIR"], "locale", get_language_label("german"))
    assert get_language_folder("german") == path


def test_get_link_for_message():
    """ Test labels of languages """
    folder = os.environ.get("NEST_MODEL_DIR")
    os.environ["NEST_MODEL_DIR"] = os.path.dirname(os.path.abspath(__file__))
    assert not get_link_for_message("Non Existing Message", None)

    # Query language where file is non existing
    link = get_link_for_message("The minimum load requirement is not met. Other calculations may not be available.")
    assert link
    # pylint: disable=line-too-long
    assert link == "https://www.skf.com/group/products/rolling-bearings/principles-of-rolling-bearing-selection/bearing-selection-process/bearing-size/requisite-minimum-load"
    # pylint: enable=line-too-long
    # Query language where file is existing
    link = get_link_for_message("The minimum load requirement is not met. Other calculations may not be available.",
                                "german")
    assert link
    assert "/de/" in link

    # query a link that is only available main
    link = get_link_for_message("This message is only in main")
    assert link
    assert link == "https://www.skf.com/group/support/skf-locations"

    # query a link that is only available main - but also checking german
    link = get_link_for_message("This message is only in main", "de")
    assert not link

    if folder:
        os.environ["NEST_MODEL_DIR"] = folder


def test_get_options_for_message():
    """ Test options for a given message """
    folder = os.environ.get("NEST_MODEL_DIR")
    os.environ["NEST_MODEL_DIR"] = os.path.dirname(os.path.abspath(__file__))
    assert not get_options_for_message("Non Existing Message", None)

    # Query language where file is non existing
    options = get_options_for_message("this is my message")
    assert options
    assert options[0]["url"] == "https://www.skf.com/group/support/contact"
    assert options[0]["label"] == "Contact SKF"
    assert options[0]["type"] == "preferred"
    assert options[1]["url"] == "https://www.skf.com"
    assert options[1]["label"] == "Hello"
    assert options[1]["type"] == "optional"

    # # Query language where file is existing
    options = get_options_for_message("this is my message", "german")
    assert options
    assert options[0]["url"] == "https://www.skf.com/de/support/contact"

    # query a link that is only available main
    options = get_options_for_message("This message is only in main")
    assert options
    assert len(options) == 1
    assert options[0]["url"] == "https://www.skf.com/only/here"
    assert options[0]["label"] == "How do you do"
    assert options[0]["type"] == "preferred"

    # query a link that is only available main - but also checking german
    link = get_options_for_message("This message is only in main", "de")
    assert not link

    if folder:
        os.environ["NEST_MODEL_DIR"] = folder
