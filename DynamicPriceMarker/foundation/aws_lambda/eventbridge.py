""" Simple Eventbridge interface, designed accoring to YAGNI principle

Currently, focussed on sending error information to event bidge

"""
import os
import json
import logging
import boto3
from botocore import exceptions
from foundation.utils.featurebroker import FeatureBroker
from foundation.utils.utils import log_time_spend


logger = logging.getLogger("nest.eventbridge")


class EventBridgeWrapper:
    """Wrapper for Event bridge functionality that delay intiailization only when needed"""

    _event_bridge = None

    def __init__(self, settings):
        """Constructor for the database
        Args:
            settings: containing the configuration options to connect to the event bus. eventBus is requested
        """
        self.settings = settings
        self.event_bus = self.settings.get("eventBus", "default")
        logger.info("Connecting to bus %s", self.event_bus)

    @property
    def client(self):
        """Event Bridge Property used with lazy loading and context caching"""
        if not self._event_bridge:
            self._event_bridge = boto3.client("events")
        return self._event_bridge

    # ####################################
    # Public methods - part of interface
    # ####################################

    @log_time_spend("eventbridge-publish-data")
    def send_error_event(self, error_context):
        """Send error context on Event bridge

        Event context should contain the following root members:
        statusCode, input, output

        """
        print("Sending event!!!")

        error_context["service"] = FeatureBroker.get_if_exists("ServiceName", "unknown")
        error_context["stage"] = os.environ.get("NEST_STAGE", "dev")
        error_context["version"] = os.environ.get("NEST_VERSION", "unknown")

        error_data = json.dumps(error_context)
        try:
            response = self.client.put_events(
                Entries=[
                    {
                        "Source": "test_dev_edwin",
                        "Resources": [],
                        "DetailType": "errorLog",
                        "Detail": json.dumps(error_context),
                        "EventBusName": self.event_bus,
                    }
                ]
            )

            if response["FailedEntryCount"] != 0:
                logger.error("Send Error log failed")
                print(error_context)
                print(response)

        # Two types of exceptions are thrown: ClientError exceptions and generic BotoCoreExceptions
        # In this case, we are probably not part of an exception handling routine at high level
        # since this functionality is typical used to push errors caught be exception handling
        # Let us not mask the earlier error with this one, yet continue to handle original error
        # by swallowing this    exception
        except exceptions.ClientError:
            logger.exception("Event ClientError caught")
            print("Printing event instead:")
            print(json.dumps(error_data))

        except exceptions.BotoCoreError:
            logger.exception("Generic Botocore exception caught")
            print("Printing exception instead:")
            print(json.dumps(error_data))

        except Exception:
            logger.exception("Generic python exception caught")
            print("Printing exception instead:")
            print(json.dumps(error_data))

    def put_event(self, source, detail_type, detail, resources=None):
        """
        Sends the custom event to cloud watch
        Args:
            source: Source of the event
            detail_type: Detail type for the event to identify
            detail: Event Detailed information JSON
            resources: Array of resources emitting event (Optional)

        Returns:
            True if event was sent successfully, else False
        """
        # pylint: disable=broad-except
        if not resources:
            resources = []
        try:
            print(
                f"   ******  Putting event from source: {source} with detail: {json.dumps(detail)}"
            )
            response = self.client.put_events(
                Entries=[
                    {
                        "Source": source,
                        "Resources": resources,
                        "DetailType": detail_type,
                        "Detail": json.dumps(detail),
                        "EventBusName": self.event_bus,
                    }
                ]
            )
            if response["FailedEntryCount"] == 0:
                return True
            logger.error("put_event failed to Event bus")
            print(response)
            code = response["Entries"][0]["ErrorCode"]
            message = response["Entries"][0]["ErrorMessage"]
            print(
                f"Exception in putting cloudwatch event."
                f"Error code {code}, Error Message {message}"
            )
            return False

        except exceptions.ClientError:
            logger.exception("Event ClientError caught")
            print("Printing event instead:")
            print(json.dumps(detail))
            raise


if __name__ == "__main__":
    wrapper = EventBridgeWrapper({"eventBus": "esod-event-bus-dev"})

    wrapper.send_error_event(
        {
            "statusCode": 500,
            "input": {"something": "here"},
            "output": {"response": "of application"},
            "version": "21.2-2001",
        }
    )
