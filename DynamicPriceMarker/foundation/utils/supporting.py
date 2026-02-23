""" PLEASE NOTE!!! This file is a duplicate from supporting.supporting.py

The reason I created this duplicate is because of the split of utils and stub to scaffolding. Many packages were
including model support, but were only needing stub and utils. For this reason, those parts were moved to scaffolding.

For most, this was fairly an easy operation with little adjustments to other files needed. This file was however the
exception.  And, since working from home, keeping all repos up-to-date is a bit of a small challange, I created this
duplicate to give me a little time to update all references in all subrepos.

This file is not ment to last. It is merely a temp solution. See supporting.supporting.py for the actual file and
corresponding unit test """

import logging
from foundation.utils.customexceptions import ParameterNotFound

# Local logger
logger = logging.getLogger("nest.utils")


# DO NOT MODIFY THIS FILE unless really needed. See comment at the top
def get_bearing_value(bearing, bearing_parameter, default_value=None):
    """ Get the value from the bearing

    Args:
        bearing: bearing used to update
        bearing_parameter: parameter of bearing to use
        default_value: Returned if parameter not found in bearing
    Returns:
         the value of the bearing parameter or None if not found
    """
    if bearing_parameter not in bearing:
        designation = bearing.get("designation", "unknown_designation")
        if default_value is None:
            logger.warning("Did not found %s in bearing %s", bearing_parameter, designation)
        else:
            logger.info("Did not found {} in bearing {}; using default {}".
                        format(bearing_parameter, designation, default_value))
        return default_value
    return bearing[bearing_parameter]


# DO NOT MODIFY THIS FILE unless really needed. See comment at the top
def store_bearing_value_in_model(model, parameter_name, bearing, bearing_parameter):
    """ Update the model parameter with the value from the bearing

    Args:
        model:  model to be updated
        parameter_name: parameter to be updated
        bearing: bearing to use to update
        bearing_parameter: parameter of bearing to use

    Raises:
        ParameterNotFound if parameter could not be found in bearing
    """
    try:
        model[parameter_name] = bearing[bearing_parameter]
    except KeyError as e:
        designation = bearing.get("id", "bearing")
        logger.warning("Bearing parameter not found: %s of bearing %s", bearing_parameter, designation)
        raise ParameterNotFound(e.args[0], designation)


# DO NOT MODIFY THIS FILE unless really needed. See comment at the top
def store_bearing_values_in_model(model, parameters, bearing, missing_is_error=False):
    """ Update the model parameter with the value from the bearing

    Args:
        model:  model to be updated
        parameters: list of tuples with model parameter name and bearing parameter name
        bearing: bearing to use to update
        missing_is_error: raise error is bearing value is missing or delete value from model otherwise

    Raises:
        ParameterNotFound if parameter could not be found in bearing
    """
    for item in parameters:
        try:
            model[item[0]] = bearing[item[1]]
        except KeyError as e:
            designation = bearing.get("id", "bearing")
            logger.warning("Bearing parameter not found: %s of bearing %s to set %s", item[1], designation, item[0])
            if missing_is_error:
                raise ParameterNotFound(e.args[0], designation)
            elif item[0] in model:
                del model[item[0]]


# DO NOT MODIFY THIS FILE unless really needed. See comment at the top
def store_bearing_value_in_model_if_exists(
        model,
        parameter_name,
        bearing,
        bearing_parameter,
        default_value=None,
        remove_if_not_available=False):
    """ Update the model parameter with the value from the bearing

    if the parameter does not exists in bearing there are two options:
    1. remove_if_not_available is true. Then parameter_name will be removed from model.
    2. remove_if_not_available is false. then the default_value will be
    stored in model[parameter_name]. In both cases false will be returned

    Args:
        model:  model to be updated
        parameter_name: parameter to be updated
        bearing: bearing to use to update
        bearing_parameter: parameter of bearing to use
        default_value: in case the parameter is not in the bearing, the default value will be set. Even if 'None'
        remove_if_not_available: (boolean) if bearing_parameter is not available in bearing then remove \
        parameter_name from model instead of setting to devault_value
    Returns:
         False if not set, true is set
    """
    try:
        model[parameter_name] = bearing[bearing_parameter]
        return True
    except KeyError as e:
        logger.debug("bearing parameter %s not found (%s) in %s", bearing_parameter, e, bearing)
        logger.warning("Bearing parameter %s not found in bearing %s",
                       bearing_parameter,
                       bearing.get('id', "unknown"))
        if remove_if_not_available:
            if parameter_name in model:
                del model[parameter_name]
        else:
            model[parameter_name] = default_value
        return False
# DO NOT MODIFY THIS FILE unless really needed. See comment at the top
