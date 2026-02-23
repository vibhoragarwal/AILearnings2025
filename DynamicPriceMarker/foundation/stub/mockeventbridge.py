""" Versy siple class to mock SQS - but only from caller side. Does nto publish anuthing for real """

import os
import copy

from foundation.utils.featurebroker import FeatureBroker
from typing import List


class MockEventBridge:
    """Simple Mock for SQS -- for now one queue - but this might change in future to queue per url"""

    def __init__(self, settings=None):
        if settings:
            self.store = settings.get("store", False)
        else:
            self.store = False
        self.queue = []
        self.event_bus = "default"

    def send_error_event(self, error_context):
        """SQS to publish the model to reporting
        Args:
            error_context: Error context to send. Should contain statusCode, input, output
        """
        error_context["service"] = FeatureBroker.get_if_exists("ServiceName", "unknown")
        error_context["stage"] = os.environ.get("NEST_STAGE", "dev")
        error_context["version"] = os.environ.get("NEST_VERSION", "unknown")

        print(error_context)
        if self.store:
            self.queue.append(copy.deepcopy(error_context))

    def put_event(self, source: str, detail_type: str, detail: dict, resources: List[str]=None):
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
        print("")
        print(detail_type, detail)
        print(resources)
        # Always store these event
        self.queue.append({"source": source, "detail_type": detail_type, "detail": copy.deepcopy(detail), "resources": resources})
        return True
