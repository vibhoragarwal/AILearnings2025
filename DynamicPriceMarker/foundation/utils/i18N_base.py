import gettext
import os
import json

# To add a language see file newLanguage.md in dictionary

SUPPORTED_LANGUAGES = {
    "default": "en_GB.UTF-8",
    "english": "en_GB.UTF-8",
    "german": "de.UTF-8",
    "chinese": "zh.UTF-8",
    "italian": "it.UTF-8",
    "spanish": "es.UTF-8",
    "french": "fr.UTF-8",
    "portuguese": "pt.UTF-8",
    "japanese": "ja.UTF-8",
    "korean": "ko.UTF-8",
    "swedish": "sv.UTF-8"
}

ISO_CODES = {
    "en": "english",
    "de": "german",
    "zh": "chinese",
    "it": "italian",
    "es": "spanish",
    "fr": "french",
    "pt": "portuguese",
    "ja": "japanese",
    "ko": "korean",
    "sv": "swedish"
}

current_lang = None


class Lang:
    """ Used as initial setup. No translation defined """

    @staticmethod
    def null_translation(message):
        return message

    gettext = null_translation


class DelegateTranslation(object):
    """ An executable class to wrap language translation. This way, we can change
    dynamically the language with a different one
    """

    def __init__(self, instance):
        self.instance = instance

    def __call__(self, message):
        return self.instance.gettext(message)


def return_string(string_value):
    """ This function just returns the string, but is used to identify translatable strings"""
    return string_value


# This code does not only register string for translation, but also does the translation
# _ = DelegateTranslation(Lang)


# This code does register the string for translation, but does not translate it
# pep8 suggest not to use a lambda for this
_ = return_string
translate = DelegateTranslation(Lang)


def get_language_folder(language):
    """ Get the language folder to download files from.

    if language is None, the main folder is used in stead - no language specifics then
    """
    if language:
        label = get_language_label(language)
        folder = os.path.join(os.environ["NEST_MODEL_DIR"], "locale", label)
    else:
        folder = os.path.join(os.environ["NEST_MODEL_DIR"], "locale")
    return folder


def get_language_label(language):
    """ get the label corresponding to language (either ISO code or label)"""
    if language not in SUPPORTED_LANGUAGES:
        language = ISO_CODES.get(language, "default")
    return SUPPORTED_LANGUAGES[language]


def get_language_iso_code(language):
    """ Get the ISO code corresponding to the supported language, or return english as default """
    return next((key for key, item in ISO_CODES.items() if item == language), "en")


def change_language(setlanguage="default", domain="global-catalog", localedir="locale/"):
    """ Switch UI language

    Args:
        setlanguage: Language that must be set - perhaps newlanguage would have been better name
        domain: MO Domain = always ise global-catalog
        localedir: Folder where locale data is stored
    Returns:
        the language that is used. Can differ from setLanguage
    """
    global current_lang
    if setlanguage not in SUPPORTED_LANGUAGES:
        if setlanguage in ISO_CODES:
            setlanguage = ISO_CODES[setlanguage]
        else:
            # Note: The language is not always set on higher levels
            setlanguage = "default"

    if current_lang == setlanguage:
        return setlanguage
    else:
        print(f"i18N: Switching to {setlanguage} ")
    language_set = SUPPORTED_LANGUAGES[setlanguage]

    # By default check NEST_MODEL_DIR. only fall back when this leads to nothing
    full_path = os.path.join(os.environ.get("NEST_MODEL_DIR", "."), localedir)
    if not os.path.isdir(full_path):
        if os.path.isdir(localedir):
            full_path = localedir

    system_language = gettext.translation(domain, localedir=full_path, languages=[language_set], fallback=True)
    system_language.install()

    def activate_translation():
        Lang.gettext = system_language.gettext

    activate_translation()
    current_lang = setlanguage
    return setlanguage


def get_link_for_message(message, language="default"):
    # Flow:
    # Check link in language specific file. If present: return link
    # if either file or link  is not present, check language independent file
    # if not present, return none
    links_list = get_links_from_file("message_links.json", language)
    if links_list:
        return links_list.get(message, None)
    return None


def get_options_for_message(message, language="default"):
    """ Get the options related to a given message """
    links_list = get_links_from_file("option_links.json", language)
    if links_list:
        return links_list.get(message, None)
    return None


def get_links_from_file(json_file="message_links.json", language=None):
    """ Get the file with the links for a given message """
    folder = get_language_folder(language)
    file_path = os.path.join(folder, json_file)
    if os.path.exists(file_path):
        with open(file_path, "r") as message_file:
            return json.load(message_file)
    return None


def convert_langauge_abbrevs(languages: list) -> list:
    """Convert languages from short form into english form"""
    path = os.path.dirname(__file__)
    with open(os.path.join(path, "languages.json"), "r", encoding="UTF-8") as json_input:
        known = json.load(json_input)
    # If a language is not known - silently ignore it
    return [known(language) for language in languages if language in known]
