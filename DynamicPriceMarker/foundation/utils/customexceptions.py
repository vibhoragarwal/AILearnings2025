import json
import logging.config

# import os #Todo:i18N: uncomment for activation of i18N-multi-language

config = None
logger = logging.getLogger("nest")

# Standard response for authorization error: No details
NO_ACCESS = "Access denied"
NO_AUTHORIZATION = "Unauthorized"
UNAUTHORIZED = "No authorization header found"
THROTTLED = "Throttled"
INVALID_SIGNATURE = "Invalid signature"
EXPIRED_TOKEN = "Expired token"


# Todo:i18N: uncomment for activation of i18N-multi-language
# # # # # Setup language
# # TODO: Implement _ macro Status Done!
# from utils.i18N_base import _


class AbortMyRequest(Exception):
    """Custom exception to replace the abort handler to clean up first
    low lever error, should not be used in business layer. Please use one of the more custom errors below
    """
    
    def __init__(self, my_error_code, my_message=""):
        """ Constructor

        """
        Exception.__init__(self, my_message)
        ## HTML error code that should be returned
        self.my_error_code = my_error_code
        ## Message (optional) for further explanation
        self.my_message = my_message
        logger.warning("Abort Request (%s) because of %s", my_error_code, my_message)

    def __str__(self):
        """ Conversion to string

        """
        return str(self.my_error_code) + ": " + self.my_message


class ParameterNotFound(Exception):
    """Legacy Error. It is Preferred to use ModelKeyError instead of reporting missing keys

    This error generates a 404, which is actually not correct and the parameter is not a resource

    """

    def __init__(self, parameter, owner=None, my_message=None):
        """ Constructor

        Args:
            parameter: [string] Name of the failing key
            owner: [string] (Grand) parent where the key as searched
            my_message: [string] optional extra message
        """
        if my_message:
            message = str(my_message)
        elif owner:
            message = "Key {} not found in {}".format(parameter, owner)
        else:
            message = "{} not found".format(parameter)

        super(ParameterNotFound, self).__init__(message)
        ## Message (optional) for further explanation
        self.my_message = message
        logger.warning(message)

    def __str__(self):
        """ Conversion to string

        """
        return str(self.my_message)


class ValidationError(Exception):
    """ Custom exception to report validation errors using a more descriptive message towards end users.

    This is the preferred way of reporting issues in input back to users, together with ModelInputError and
    ModelValueError
    """

    def __init__(self, model, validationIssues):
        """ Constructor

        Args:
            model: model that contained the issues
            validationIssues: [Dict|List] dictionary or list of dicts with parameter and corresponding issues
            Expecting the following fields field, message, status like

            ValidationError(model, {"field": "shaftOrientation",
                                          "message": "Bearing arrangement value not valid",
                                          "status": "validation error"}

        """
        self.json = validationIssues
        message = json.dumps(validationIssues)
        # Alternative to do it in one line
        # message = ",".join(':'.join(_) for _ in validationIssues.items())
        super(ValidationError, self).__init__(message)
        # descriptive message describing issues with validation
        self.my_message = message
        logger.warning("%s using data %s", message, model)

    def __str__(self):
        """ Conversion to string

        """
        return self.my_message

class ModelValidationError(ValidationError):
    """Custom exception to report validation errors to end user using a more descriptive message.

    This is the preferred way of reporting issues in input back to users, together with ModelInputError and
    ModelValueError.
    
    For messages to be translatable to other languages, do not use messages constructed with f-strings, but 
    use the predefined messages listed above.
    """
    
    def __init__(self, field: str, message: str, container: str|None = None, status="validation error", value=None, param_range=None):
        """Specific imputs to ValidationError

        Args:
            field: [string] Name of the failing key
            message: [string] Message describing the issue
            container: [string] all parents concatinated with a dot when applicable Like parent.child.1.grandchild
            status: [string] Status of the issue
            value: [string] Value found in the field that does not comply with expectations
            param_range: [string] Range of the issue that the value should be in
        """
        validation_issue = {
            "field": field,
            "message": message,
            "status": status,
        }
        if container is not None:
            validation_issue["container"] = container
        if value is not None:
            validation_issue["value"] = str(value)
        if param_range is not None:
            validation_issue["range"] = param_range
        
        super(ModelValidationError, self).__init__(None, validation_issue)



class ModelSetupError(ValidationError):
    """ Custom exception to report setup model errors - meant as an internal error 500 - not a 422

    This error is typically flagged when a problem with the model setup has been detected that cannot be
    resolved by any user action. It is an unrecoverable error that needs to be fixed in the model setup.
    Most likely, the metadata.
     """

    def __init__(self, model, validationIssues):
        """ Constructor

        Args:
            model: model that contained the issues
            validationIssues: [dict] dictionary with parameter and corresponding issues
        """
        super(ModelSetupError, self).__init__(model, validationIssues)


class ConfigurationError(Exception):
    """ Custom exception to report a database error like collection not found or write error. Configuration relates
    here to configuration of external resources like AWS resources and the likes.

    Generates a 500 internal error, as the input in correct, See also ModelSetupError
    """

    def __init__(self, item, message):
        """ Constructor

        Args:
            item: [string] Configuration item in error
            message: [string] message describing the event
        """
        error_message = "Configuration error on item {0}: {1}".format(item, message)

        # Todo:i18N: uncomment for activation of i18N-multi-language
        # _error_message = _("Configuration error on item {0}: {1}")
        # error_message = _error_message.format(item, message)

        super(ConfigurationError, self).__init__(error_message)
        # descriptive message describing issues with validation
        self.my_message = message
        logger.error(error_message)


class ItemNotFound(Exception):
    """ Custom exception to report that a resource has not been found, like an bearing in database, or model in database

    This will generate a 404 error
    """

    def __init__(self, item, error_message=None, log_error=True):
        """ Constructor

        Args:
            item: [string] Item not found
        """
        if not error_message:
            error_message = f"Item not found: {item}"

        # # Todo:i18N: uncomment for activation of i18N-multi-language
        # _error_message = _("Item not found: {0}")
        # error_message = _error_message.format(item)

        super(ItemNotFound, self).__init__(error_message)
        # descriptive message describing issues with validation
        self.my_message = error_message
        if log_error:
            logger.error(error_message)

class ActionNotAllowed(Exception):
    """ Custom exception to report an invalid operation, generates a 403 error

    see also CalculationNotSupported error for a particular ActionNotAllowed
    """

    def __init__(self, item=None):
        """ Constructor

        Args:
            item: [string, optional] Action is not allowed
        """
        if item:
            error_message = f"Operation is not allowed: {item}"
        else:
            error_message = NO_AUTHORIZATION

        # # Todo:i18N: uncomment for activation of i18N-multi-language
        # _error_message = _("Operation is not allowed: {0}")
        # error_message = _error_message.format(item)

        super(ActionNotAllowed, self).__init__(error_message)
        # descriptive message describing issues with validation
        self.my_message = error_message
        logger.error(error_message)


class CalculationNotSupported(Exception):
    """ Custom exception to report that a particular calculation is not supported with the given input.

    Most likely, it is related to a calculation that does not match a particular bearing type or designation

    At this moment, it generates a 404 meaning in this case, calculation not found. Might be changed
    """

    def __init__(self, item, calculation):
        """ Constructor

        Args:
            item: [string] Action is not allowed
        """
        error_message = "Calculation {1} is not supported for {0}".format(calculation, item)

        # # Todo:i18N: uncomment for activation of i18N-multi-language
        # _errormessage = _("Calculation {1} is not supported for {0}")
        # error_message = _errormessage.format(calculation, item)

        super(CalculationNotSupported, self).__init__(error_message)
        # descriptive message describing issues with validation
        self.my_message = error_message
        logger.error(error_message)


class HTTPConnectionError(Exception):
    """ Custom exception to report a database error like collection not found or write error
    This error should be used sparingly, and should be reserved to HTTP layer processing only
    """

    def __init__(self, host, errorCode, message):
        """ Constructor

        Args:
            host: [string] Name of the host we are trying to connect
            errorCode: [string] Specific Error code if any
            message: [string] message describing the event
        """
        error_message = "Connection error ({1}): {0} while trying to access to {2}".format(message, errorCode, host)

        # # Todo:i18N: uncomment for activation of i18N-multi-language
        # _errormessage = _("Connection error ({1}): {0} while trying to access to {2}")
        # errormessage = _errormessage.format(message, errorCode, host)

        super(HTTPConnectionError, self).__init__(error_message)
        # descriptive message describing issues with validation
        self.my_message = error_message
        self.my_error_code = errorCode


class AuthorisationError(Exception):
    """Custom exception to replace announce that there is no access to the particular resource or calculation"""

    def __init__(self, my_message=NO_ACCESS,  error_message=None):
        """ Constructor

        """
        Exception.__init__(self, my_message)
        # Message (optional) for further explanation
        self.my_message = my_message
        self.error_message = error_message
        logger.warning("AuthorisationError: %s - %s", my_message, error_message or "")

    def __str__(self):
        """ Conversion to string

        """
        return self.my_message


class RuntimeSubprocessError(Exception):
    """Custom exception to capture Runtime error with
    any additional I/O files to process, for tracking """

    def __init__(self, my_message: str, log_files: dict = None, messages: dict = None):
        """ Constructor

        Args:
            my_message: message
            log_files: files to upload with file key and file path
            messages : messages in json format (can contain errors, warnings etc.)
        """
        super().__init__(my_message)

        logger.warning("  ======  RuntimeSubprocessError =====")
        logger.warning(my_message)
        logger.warning(log_files)
        logger.warning(messages)
        logger.warning("  ======  ====================== =====")

        self.message = my_message
        self.logfiles = log_files

        if messages:
            # wrapping to message key needed as framework would need this
            self.messages = {"message": messages}
        else:
            self.messages = {}


class SubprocessTimeoutError(Exception):
    """Custom exception when a subprocess timeout occurred"""

    def __init__(self, my_message: str, log_files: dict = None, messages: dict = None):
        """ Constructor

        Args:
            my_message: message
            log_files: files to upload with file key and file path
            messages : messages in json format (can contain errors, warnings etc.)
        """
        super().__init__(my_message, log_files, messages)


class ModelInputError(Exception):
    """Exception to report structural changes in the input model.
    """

    def __init__(self, parameter, my_message):
        """Constructor
        Args:
            parameter: [string] Name of the failing key
            my_message: [string] optional extra message
        """
        # Self.json is a list of  Validation error type
        self.json = None
        message = "Issue detected in Error setup"
        if isinstance(my_message, str):
            message = f"{parameter}: {my_message}"
        elif isinstance(my_message, dict):
            message = f"{my_message['parameter']}: {my_message['detail']}"
            self.json = [my_message]
        elif isinstance(my_message, list):
            # Assume uniform list
            if isinstance(my_message[0], str):
                message = f"{parameter}: {my_message[0]}"
            elif isinstance(my_message[0], dict):
                if 'parameter' in my_message[0]:
                    message = f"{my_message[0]['parameter']}: {my_message[0]['detail']}"
                if 'field' in my_message[0]:
                    message = f"{my_message[0]['field']}: {my_message[0]['detail']}"
                self.json = my_message

        super(ModelInputError, self).__init__(message)
        self.my_message = message
        logger.warning(message)
        logger.info(my_message)

    def __str__(self):
        """Conversion to string"""
        return str(self.my_message)


class ModelValueError(Exception):
    """Custom exception to capture model errors in a more descriptive way

    Generates a 422 - meaning that the user will be able to retry with value for the given parameter
    """

    def __init__(self, value, my_message):
        """ Constructor

        Args:
            value: Parameter that caused the error
            my_message: Reason of failure
        """
        super(ModelValueError, self).__init__(my_message)
        self.my_message = my_message
        self.my_value = value
        logger.warning(f"{value}: {my_message}")

    def __str__(self):
        """ Conversion to string

        """
        return str(f"{self.my_value}: {self.my_message}")


class ModelResultError(Exception):
    """Custom exception to be raised when a calculation failed for other then user error
    """

    def __init__(self, my_message):
        """ Constructor

        Args:
            my_message: Reason of failure
        """
        super(ModelValueError, self).__init__(my_message)
        self.my_message = my_message

    def __str__(self):
        """ Conversion to string

        """
        return str(self.my_message)


class InputError(Exception):
    """Custom exception to capture General Input errors other than ModelInputErrors. E.g. for use with non model related functions

     Generated a 400, General input error - less specific than the 422 we use to describe model input and validation errors
     """

    def __init__(self, my_message):
        """ Constructor

        Args:
            parameter: [string] Name of the failing key
            my_message: [string] optional extra message
        """
        message = f"Input Error: {my_message}"

        super().__init__(message)
        self.my_message = message
        logger.warning(message)

    def __str__(self):
        """ Conversion to string

        """
        return str(self.my_message)
