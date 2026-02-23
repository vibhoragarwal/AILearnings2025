""" Simple SQS interface, designed accoring to YAGNI principle

Only build stuff that I need at the time that I need it

Uses NEST_SQS_TOPIC to identify the bucket if no bucket is given while creating the wrapper

This could use a litle refactoring to make it simpler, e.g one input for sqs name

"""
import os
import uuid
import logging
import json
import boto3
from foundation.utils.utils import log_time_spend
from foundation.utils.customexceptions import ConfigurationError, ActionNotAllowed

from foundation.utils.featurebroker import FeatureBroker

logger = logging.getLogger("nest.s3")


class SQSWrapper:
    """
    Generic database wrapper for AWSs SQS Server - YAGNI based

    Supports both Fifo Queue and plain queue
    """

    sqs_client = None
    sqs_endpoint_client = None

    def __init__(self, settings):
        """Constructor for the database
        Args:
            settings: containing the configuration options to connect to the SQS
        """
        self.settings = settings
        if settings and "queue_url" in settings:
            queue_url = self.settings["queue_url"]
        else:
            queue_url = os.environ.get("NEST_SQS_URL")

        if not queue_url:
            # No URL, try to get it by using queue name
            queue_url = settings.get("sqs")
        # connecting to SQS requires the new SQS endpoint
        # https://github.com/boto/botocore/issues/1418
        # https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-internetwork-traffic-privacy.html
        sqs_region = os.environ.get("AWS_REGION", "eu-west-1")
        self.sqs_endpoint_url = f"https://sqs.{sqs_region}.amazonaws.com"

        if queue_url and queue_url.startswith("https://"):
            self.queue_url = queue_url
        else:
            try:
                self.queue_url = self.query_queue_url(queue_url)
            # pylint:disable=broad-except
            except Exception:
                # Some operations have the option to specify there own queue - so cannot abort here
                logger.exception("No SQS Queue found")
                self.queue_url = ""

        self.is_fifo = ".fifo" in self.queue_url
        self.message_group_id = settings.get("messageGroupId", "esod_simpro_api")
        logger.info("Connecting to sql queue_url %s", self.queue_url)
        self.default_delay = settings.get("delay_send", 0)

    @property
    def sqs(self):
        """Use lambda caching as well as lazy loading"""
        if not SQSWrapper.sqs_client:
            SQSWrapper.sqs_client = boto3.client("sqs")
        return SQSWrapper.sqs_client

    @property
    def sqs_endpoint(self):
        """Use lambda caching as well as lazy loading"""
        if not SQSWrapper.sqs_endpoint_client:
            SQSWrapper.sqs_endpoint_client = boto3.client("sqs", endpoint_url=self.sqs_endpoint_url)
        return SQSWrapper.sqs_endpoint_client

    # ####################################
    # Public methods - part of interface
    # ####################################

    # TODO: Rewrite to me more generic and reusable
    @log_time_spend("sqs-publish_data")
    def publish_data(self, message):
        """Test if the SQS is accessible right now
        Returns:
            True if database is accessible, False otherwise
        """
        print("SQS: Sending data to " + self.queue_url)
        print(message)
        if self.is_fifo:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageDeduplicationId=str(uuid.uuid4()),
                MessageGroupId=self.message_group_id,
                DelaySeconds=self.default_delay,
                MessageBody=message
            )
        else:
            if role := FeatureBroker.get_if_exists("UserRole", None):
                message = f"{message} {role}"
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                DelaySeconds=self.default_delay,
                MessageAttributes={"Message": {"DataType": "String", "StringValue": message}},
                MessageBody=(message),
            )
        print(response)
        print(response["MessageId"])

    @log_time_spend("sqs-publish_queue_data")
    def publish_queue_data(self, message, url=None):
        """SQS to publish the model to reporting - but without messageAttributes
        Args:
            url: URL of SQS Service
            message: String or dict containing the data to be send
        Returns:
            valid Message ID
        """
        if isinstance(message, dict):
            message = json.dumps(message)
        if not url:
            url = self.queue_url

        print(f"Publishing to SQS {url}: {message}")
        if self.is_fifo:
            response = self.sqs.send_message(
                QueueUrl=url,
                MessageDeduplicationId=str(uuid.uuid4()),
                MessageGroupId=self.message_group_id,
                MessageBody=message,
            )
        else:
            response = self.sqs.send_message(QueueUrl=url, MessageBody=message)

        print(f"SQS Response {response}")
        return response["MessageId"]

    def query_queue_url(self, queue_name):
        """Get the queue URL for the queue
        Args:
            queue_name: Name of the queue

        Returns:
            Queue URL
        """
        response = self.sqs.list_queues(QueueNamePrefix=queue_name)
        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            error_code = response["ResponseMetadata"]["HTTPStatusCode"]
            raise ActionNotAllowed(f"query SQS with name {queue_name}. Error code: {error_code}")

        if not response.get("QueueUrls"):
            raise ConfigurationError("SQS", queue_name)

        if len(response["QueueUrls"]) > 1:
            raise ConfigurationError("SQS (more than 1)", queue_name)

        return response["QueueUrls"][0]

    def get_available_messages_count(self):
        """Get approximate number of messages available for retrieval
        Returns:
            Number of messages available for retrieval
        """
        # TODO: Can I use endpoint_url always?
        response = self.sqs_endpoint.get_queue_attributes(
            QueueUrl=self.queue_url, AttributeNames=["ApproximateNumberOfMessages"]
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            error_code = response["ResponseMetadata"]["HTTPStatusCode"]
            raise ActionNotAllowed(f"query SQS with name {self.queue_url}. Error code: {error_code}")
        return int(response["Attributes"]["ApproximateNumberOfMessages"])


if __name__ == "__main__":
    FeatureBroker.register("UserRole", "admin")
    wrapper = SQSWrapper({"queue_url": "https://sqs.eu-west-1.amazonaws.com/172518260720/sample-queue"})
    assert wrapper.queue_url
    wrapper.publish_data("test")
