""" Very simple class to mock SQS - but only from caller side.
Does not publish anything for real """

import json
import os
import subprocess
import logging
from uuid import uuid4


logger = logging.getLogger("stub")


class MockSQS:
    """ Simple Mock for SQS -- for now one queue - but this might change in future to queue per url """

    def __init__(self, settings):
        self.queue = []
        self.queue_url = settings.get("queue_url", "sqs://mock.me/") if settings else "sqs://mock.me/"
        self.path = settings.get("path", None) or None
        self.container_id = settings.get("container_id", None) or None
        self.message_id = 0
        if self.path:
            os.makedirs(self.path, exist_ok=True)

    def publish_queue_data(self, message, url=None):
        """SQS to publish the model to reporting
        Args:
            url: URL of SQS Service
            message: String containing the data to be sent
        Returns:
            valid Message ID
        """

        if isinstance(message, dict):
            message_str = json.dumps(message)
        elif isinstance(message, str):
            message_str = message
        else:
            raise ValueError("message must be a dict or a string")

        # Case used of field attributes is same as in SQS Boto3
        message = {
            "MessageId": str(uuid4()),
            "MessageBody": message_str
        }

        if not url:
            url = self.queue_url

        self.queue.append(message)
        self.message_id += 1

        # print(f"Publishing to Mock SQS {url}: {message}")

        if self.path:
            filename = self.write_message(message)
            if self.container_id:
                self.write_message_to_container(filename)

        return str(message["MessageId"])

    def publish_data(self, message):
        """SQS to publish the message
        Args:
           message: String containing the data to be sent
        Returns:
           valid Message ID
        """
        return self.publish_queue_data(message)

    def write_message(self, message):
        """ Write message with messageId to path"""

        filename = os.path.join(self.path, message["MessageId"] + ".json")
        with open(filename, "w", encoding="utf-8") as json_out:
            json.dump(message, json_out, indent=2, sort_keys=True)
        print("wrote sqs mock file to ", filename)
        return filename

    def write_message_to_container(self, filename):
        """Write message with messageId to path in the given container - only for testing
        Args:
            filename: such as  /tmp/sqs/55aab1bc-8d7c-49d2-9c4c-9d57d4d7badf.json

        Returns:
            filename as in request
        """

        dir_path = os.path.dirname(filename)

        print(f'write {filename} in container {self.container_id} under dir path {dir_path}')

        # destination directory should exist, create it before copy
        command_line = ["docker", "exec", "-d", self.container_id, "mkdir", "-p", dir_path]
        result = subprocess.run(command_line, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        check_for_error(result, "Writing message file to container failed in creating destination")

        command_line = ["docker", "cp", filename, self.container_id + ":" + filename]
        result = subprocess.run(command_line, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        check_for_error(result, "Writing message file to container failed")

        if result.stdout:
            logger.info("Writing message file into docker: %s", result.stdout.decode("utf-8"))

        print('create done')

        return filename


def check_for_error(result: subprocess.CompletedProcess, message: str):
    """Raise exception for error
    Args:
        result: sub process result
        message: error message
    """
    if not result.stderr:
        return
    if "[ERROR]" not in result.stderr.decode("utf-8"):
        # Most likely cause of error:
        print(result.stderr)
        raise Exception(message)
