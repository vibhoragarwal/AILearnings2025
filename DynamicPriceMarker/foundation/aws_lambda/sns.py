""" Simple S3 interface, designed accoring to YAGNI principle

Only build stuff that I need at the time that I need it

Uses NEST_SNS_TOPIC to identify the bucket if no bucket is given while creating the wrapper

"""
import os
import logging
import boto3
from foundation.utils.customexceptions import ItemNotFound
from foundation.utils.utils import log_time_spend


logger = logging.getLogger("nest.sns")


class SNSWrapper:
    """
    Generic database wrapper for AWSs SNS Server - YAGNI based
    @ingroup aws_lambda
    """
    sns_client = None

    def __init__(self, settings):
        """Constructor for the database
        Args:
            settings: containing the configuration options to connect to the database
        """
        self.settings = settings
        self.topic = self.settings.get("topic", os.environ.get("NEST_SNS_TOPIC"))
        self.topic_arn = self.resolve_topic_arn(self.topic)
        logger.info("Connecting to topic %s", self.topic_arn)

    @property
    def sns(self):
        """Use Lambda caching and lazy creation"""
        if not SNSWrapper.sns_client:
            SNSWrapper.sns_client = boto3.client('sns')
        return SNSWrapper.sns_client

    def resolve_topic_arn(self, match):
        """ Find SNS  topic matching match """
        topics = self.sns.list_topics()
        found = next((item["TopicArn"] for item in topics["Topics"] if match in item["TopicArn"]))
        if not found:
            raise ItemNotFound(f"SNS Topic {match}")
        return found

    # ####################################
    # Public methods - part of interface
    # ####################################

    @log_time_spend("sns-publish-data")
    def publish_data(self, source_data):
        """ Publish data to SNS
        """
        put_data = {
            "TopicArn": self.topic_arn,
            "Message": source_data
        }
        self.sns.publish(**put_data)

    @log_time_spend("sns-publish-email-data")
    def publish_email_data(self, subject: str, message: str):
        """publish a typical message for email subscribers.
        subject is the 'Subject' line when the message is delivered to email endpoints.
        This field will also be included, if present, in the standard
        JSON messages delivered to other endpoints.
        """
        self.sns.publish(
            TopicArn=self.topic_arn,
            Message=message,
            Subject=subject,
        )
        print(f'done to topic {self.topic_arn}')



if __name__ == "__main__":
    wrapper = SNSWrapper({"topic": "esod-translation-published"})
    assert wrapper.topic_arn
    wrapper.publish_data("Welcome world")
