# Internationalization (i18N) and localization (l10n)
#
# In computing, internationalization and localization are means of adapting
# computer software to different languages, regional differences and technical
# requirements of a target locale. 
#
# - Internationalization is the process of
# designing a software application so that it can be adapted to various
# languages and regions without engineering changes. Localization is the
# process of adapting internationalized software for a specific region or
# language by translating text and adding locale-specific components.
#
# - Localization (which is potentially performed multiple times, for different
# locales) uses the infrastructure or flexibility provided by
# internationalization (which is ideally performed only once, or as an
# integral part of ongoing development)
#
# Source: https://en.wikipedia.org/wiki/Internationalization_and_localization

import gettext
import os
from foundation.utils.i18N_base import Lang, change_language

from foundation.utils.featurebroker import FeatureBroker
libpath = os.environ.get("NEST_LIB_PATH", ".")

# # # Setup multi language support
        # I18n = internationalization
        # L10n = localization
        # examples environment variables
                # LC_MEASUREMENT=nl_NL.UTF-8
                # LC_PAPER=nl_NL.UTF-8
                # LC_MONETARY=nl_NL.UTF-8
                # LANG=en_US.UTF-8
                # LC_NAME=nl_NL.UTF-8
                # LC_ADDRESS=nl_NL.UTF-8
                # LC_NUMERIC=nl_NL.UTF-8
                # LC_TELEPHONE=nl_NL.UTF-8
                # LC_IDENTIFICATION=nl_NL.UTF-8
                # LC_TIME=nl_NL.UTF-8

#
# # # Setup language  
DOMAIN = "global-catalog"
LOCALEDIR = os.path.join(libpath, "locale/")
FeatureBroker.register("DOMAIN", DOMAIN)
FeatureBroker.register("LOCALEDIR", LOCALEDIR)
FeatureBroker.register("Language", "default")
FeatureBroker.register("LanguagePrevious", "default")

change_language(setlanguage="default", domain=DOMAIN, localedir="locale/")
