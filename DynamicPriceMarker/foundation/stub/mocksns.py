""" Very sipmle class to mock SNS - but only from caller side. Does not publish anything for real """

import os
import logging
logger = logging.getLogger("nest.mocksns")

class MockSNS:
    """ Simple Mock for SNS"""

    def __init__(self, settings):
        """Constructor for the SNS
         Args:
            settings: containing the configuration options
        """
        self.topic = settings.get("topic", os.environ.get("NEST_SNS_TOPIC", "mock_topic"))
        self.topic_arn = f'{self.topic}_arn'
        logger.info("Connecting (Mock) to topic %s", self.topic_arn)

    def publish_data(self, source_data):
        """ Publish data to SNS Mock
        """
        put_data = {
            "TopicArn": self.topic_arn,
            "Message": source_data
        }
        print("Published", put_data)

    def publish_email_data(self, subject: str, message: str):
        """publish a typical message for email subscribers.
        subject is the 'Subject' line when the message is delivered to email endpoints.
        This field will also be included, if present, in the standard
        JSON messages delivered to other endpoints.
        """
        print(f'publish data for email: with subject {subject}, message {message}')
