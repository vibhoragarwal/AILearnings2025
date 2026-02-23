"""
Configuration class in scaffolding - duct type compatible with Configuration in AWS Lambda - but contains more

This class is to handle service configuration with the general principle that every
configuration in a config file is to be overruled by an environment variable
Logging in the file is just to support the developer

@ingroup lambda
"""

import logging
import logging.config
import os

from foundation.utils.featurebroker import FeatureBroker

logger = logging.getLogger("esod")


# pylint: disable=too-few-public-methods
class Configuration:
    """Configuration class for the NEST module
    @ingroup aws_lambda
    """

    def __init__(self, service):
        """Constructor

        Args:
         service: name of this service
        """
        self.intialize_log_level()
        self.service = service
        self.user = os.environ.get("USER", "jenkins")
        FeatureBroker.register("ServiceName", service)
        self.stage = os.environ.get("NEST_STAGE", "dev")
        # Stage might not be set in developer environment
        FeatureBroker.register("Stage", self.stage)
        FeatureBroker.register("config", self)

        if "NEST_VERSION" in os.environ:
            print(f"Starting {service}: {os.environ['NEST_VERSION']}")
        else:
            print(f"Missing NEST_VERSION for {service} - using default")
            os.environ["NEST_VERSION"] = "0.0.1"

    def intialize_log_level(self):
        """Initialize the log level

        Initialize the log level from the environment variable NEST_LOG_LEVEL if it exists
        """
        log_level = os.environ.get("NEST_LOG_LEVEL", "INFO")
        logging.basicConfig(level=log_level)
        logger.info("Log level set to %s", log_level)

        loglevel_string = os.environ.get("LOGLEVEL")
        if loglevel_string:
            print(f"Got LOGLEVEL ({loglevel_string}) from env")
            root = logging.getLogger()
            default_level = root.getEffectiveLevel()
            print(f"Default loglevel number: {default_level}")
            loglevel_num = getattr(logging, loglevel_string.upper(), default_level)
            print(f"New loglevel number: {loglevel_num}")
            if loglevel_num != default_level:
                print(f"Setting loglevel to {loglevel_num}")
                logging.basicConfig(level=loglevel_num)
                if root.handlers:
                    for handler in root.handlers:
                        handler.setLevel(loglevel_num)

    def is_mocked_device(self, device: str, group: str = "aws") -> bool:
        """Check if the device should be mocked"""
        mocked = os.environ.get("NEST_MOCK", "").upper()
        if mocked == "ALL":
            return True
        splitted = mocked.split(",")
        splitted = [item.strip() for item in splitted]

        if group.upper() in splitted:
            return True
        if device.upper() in splitted:
            return True

        # FINAL CHECK - old style
        return os.environ.get(f"NEST_MOCK_{device.upper()}", "false").upper() == "TRUE"

    def create_device_name(self, device: str, use_user: bool = True) -> str:
        """Create a device name. For dev, if use_user is True, use the user name, otherwise use jenkins"""
        if self.stage == "dev":
            return f"esod-{self.service}-{device}-{os.environ.get('USER', 'jenkins') if use_user else 'jenkins'}-{self.stage}"
        return f"esod-{self.service}-{device}-{self.stage}"

    def get_device_name(self, device: str, use_user: bool = True) -> str:
        """Create a device name. For dev, if use_user is True, use the user name, otherwise use jenkins"""
        if name := os.environ.get(f"NEST_{device.upper()}_NAME"):
            return name
        return self.create_device_name(device, use_user)

    def get_device_arn(self, device: str) -> str:
        """Create a device name. For dev, if use_user is True, use the user name, otherwise use jenkins"""
        # Arn should always be specified
        return os.environ.get(f"NEST_{device.upper()}_ARN")
