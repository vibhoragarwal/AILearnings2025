""" Mocks S3.py - S3Wrapper methods
There could be instances when the service wants to mock S3 connection, then
this class can be used

An example, the S3 mocking is used when testing against docker so as to avoid
dependencies such as on AWS while running business logic tests
"""

import os
import time
import logging
import shutil
import subprocess
import datetime
import random

from foundation.utils.customexceptions import ItemNotFound

logger = logging.getLogger("nest.mocks3")

#pylint: disable=unused-argument

class MockS3Wrapper:
    """ Simple Mock for S3"""

    def __init__(self, settings):
        """Constructor for the database
        Args:
            settings: containing the configuration options to connect to the database
        """
        self.settings = settings
        self.bucket_name = self.settings.get("bucket", os.environ.get("NEST_S3_BUCKET"))
        self.container_id = self.settings.get("container_id", "")
        self.path = settings.get("path")
        if self.path:
            self.ensure_path_exists(settings.get("clear", False))

        logger.info("Mock Connecting to bucket %s", self.bucket_name)

    def upload_data(self, source_data, target_name):
        """ upload_data using target_name as filename. Data is either nbinary data or a string
        """
        logger.info("Mock upload_data with key %s", target_name)

        if self.path:
            mode="w" if isinstance(source_data, str) else "wb"
            file_path = os.path.join(self.path, target_name)
            if not os.path.exists(os.path.dirname(file_path)):
                print(f"Creating dir: {os.path.dirname(file_path)}")
                os.makedirs(os.path.dirname(file_path))
            with open(file_path, mode, encoding="utf-8") as fileout:
                fileout.write(source_data)


    def upload_zip_file(self, source_zip_path, zip_file_name, target_s3_bucket):
        """ upload_zip_file
        Args:
            source_zip_path: path of zipped file
            zip_file_name: zip file name
            target_s3_bucket: the bucket to upload to

        """
        logger.info("Mock upload_zip_file with zip_file_name %s, target_s3_bucket %s", zip_file_name, target_s3_bucket)


    def upload_to_unique_file(self, source_data, base_name, extension, folder_name=None):
        """ Uploads data with a unique file name

        """
        self.upload_data(source_data, "file_name")

    def upload_to_folder(self, source_data, folder_name, filename):
        """ Uploads source data to mocked s3 and generated a unique foldername
         if no foldername is given

        foldername will be base_name/timeisms/
        use file path is then base_name/timeinms/filename

        Args:
            source_data: source data format in a way that is can be saved. e.g. string
            folder_name: parent folder name used to store filename in
            filename: the name that needs to be used to save the source_data in the unique folder

        """
        # Since we are not working on local OS, I do not use os.path tools
        file_path = folder_name + "/" + filename
        self.upload_data(source_data, file_path)

    def upload_zip_to_folder(self, source_zip_path, zip_file_name, target_s3_folder):
        """ upload_zip_to_folder
        Args:
            source_zip_path: path of zipped file
            zip_file_name: zip file name
            target_s3_bucket: the bucket to upload to

        """
        self.upload_zip_file(source_zip_path, zip_file_name, target_s3_folder)

    @staticmethod
    def create_unique_filename(base_name, extension, folder_name=None):
        """  filename = base_name + "_" + current_time + "." + extension
        """
        current_time = int(round(time.time() * 1000))
        filename = f"{base_name}_{current_time}.{extension}"

        if folder_name:
            filename = folder_name + "/" + filename
        return filename

    @staticmethod
    def create_unique_foldername(base_name=None):
        """  filename = base_name + "_" + current_time + "." + extension
        """
        # Take current time in milliseconds. This should be enough uniqueness
        # for 99.999% of the cases
        current_time = int(round(time.time() * 1000))
        if base_name:
            folder_name = f"{base_name}/{current_time}"
        else:
            folder_name = str(current_time)
        return folder_name

    def upload_file_to_s3(self, key, filepath):
        """ Upload file to S3 mock
        Args:
            key upload key
            filepath file to be uploaded
        """
        print(f'Mock upload_file_to_s3 key {key}, filepath {filepath}')
        # mimic actual boto client which throws err if no file
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"file at path {filepath} not found")
        logger.info("Mock upload_file_to_s3 key %s, filepath %s", key, filepath)
        if self.container_id:
            self.upload_file_to_container(filepath, key)
        elif self.path:
            path =  os.path.join(self.path, key)
            dirname = os.path.dirname(path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            shutil.copy(filepath, os.path.join(self.path, key))


    def does_key_exists(self, key):
        """ Method to check if a key exists in s3
        Args:
            key: key for the S3 File
        Returns:
           True if key exists, else False
        """
        print(f'Mock does_key_exists key {key}, return True')
        return True


    def generate_presigned_url(self, key, additional_params=None, is_read=True):
        """ Method to mock generate signed URL
        Args:
           key: key to get S3 File
        Returns:
           Mocked Signed S3 URL
        """
        print(f'returning mocked generate_presigned_url for {key}')
        return "https://mocked.signed.url/"+key+"?AWSAccessKeyId=mocked_access_key&Signature=mocked_sign&Expires=100"

    def generate_presigned_post(
        self,
        object_name: str,
        fields: dict = None,
        conditions: list = None,
        expiration: int = 3360,
    ) -> dict | None:
        """Generate a mock presigned URL S3 POST request to upload a file

        Args:
            object_name:    Name of the object that should hold the uploaded
                            data, a file name for example.
            fields:         Dictionary of prefilled form fields
            conditions:     List of conditions to include in the policy
            expiration:     Time in seconds for the presigned URL to remain
                            valid

        Returns: Dictionary with the following keys:
            url:    URL to post to
            fields: Dictionary of form fields and values to submit with the POST

        Errors:
            Real request would raise ClientError if something goes wrong and return
            None.

        """
        print(f"returning mocked generate_presigned_post for {object_name}")
        return {
            "url": "https://<bucket_name>.<aws_host>.mocked.signed.url/",
            "fields": {
                "Content-Type": fields.get("Content-Type", "application/json"),
                "key": object_name,
                "x-amz-algorithm": "mock_aws_algo",
                "x-amz-credential": "mock_aws_credential",
                "x-amz-date": "20251107T091628Z",
                "x-amz-security-token": "mock_aws_token",
                "policy": "mock_policy_string",
                "x-amz-signature": "mock_signature",
            },
        }

    def download_file(self, object_name, location=None):
        """ Method to mock downloading file from S3
        Args:
           object_name: S3 based object name (e.g. filename)
           location: Place where file needs to be downloaded from
        Returns:
           saved location
        """

        location = location or self.path or "/tmp/s3"
        filename = os.path.join(location, object_name)

        if self.container_id:
            return self.download_file_from_container(filename)
        print(f'returning path where file would reside - need to create a sample file? {object_name}')
        return filename

    def load_file(self, filename, version=None):
        """ Method to mock loading file from S3
        Args:
           object_name: S3 based object name (e.g. filename)
        Returns:
           file content
        """
        # Note version is not supported in mock
        if self.container_id:
            filename = os.path.join("/tmp/s3", filename)
            self.download_file_from_container(filename)
        elif self.path:
            filename = os.path.join(self.path, filename)
        else:
            return "mocked file content"

        with open(filename, "r") as file:
            return file.read()


    def download_file_by_version(self, object_name, version_id, location=None):
        """ Download an object from S3 and store it in location

        Args:
            object_name: Name of object to download from S3 (filename)
            version_id: verison to get - not supported on mock
            location: Location to store the downloaded file (None specified - /tmp will be used)
        Returns:
            path of downloaded file - of object_name only filename part is used
        """
        logger.info("Ignoring version")
        return self.download_file(object_name, location)

    def download_file_from_container(self, filename):
        """ Write message with messageId to path in the given container - only for testing"""
        command_line = ["docker", "cp", self.container_id + ":" + filename, filename]

        # print(f'try downloading {filename} from container {self.container_id}')

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        result = subprocess.run(command_line, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        check_for_error(result, "Download file from container failed")

        if result.stdout:
            logger.info("Download file from docker: %s", result.stdout.decode("utf-8"))

        print('download done')
        return filename

    def upload_file_to_container(self, filename, object_key):
        """ Write message with messageId to path in the given container - only for testing"""
        # Note that object_key should not start with a /

        file_path = os.path.join(self.path, object_key)
        dir_path = os.path.dirname(file_path)

        # destination directory should exist, create it before copy
        command_line = ["docker", "exec",  "-d", self.container_id, "mkdir", "-p", dir_path]
        result = subprocess.run(command_line, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        check_for_error(result, "Upload file to container failed in creating destination")

        command_line = ["docker", "cp", filename, self.container_id + ":" + file_path]
        print("uploading file", command_line)
        result = subprocess.run(command_line, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        check_for_error(result, "Upload file to container failed")

        if result.stdout:
            logger.info("Upload file into docker: %s", result.stdout.decode("utf-8"))
        return object_key

    def ensure_path_exists(self, clear_if_exists):
        """Create full path if does not exists"""
        if os.path.exists(self.path):
            if not clear_if_exists:
                # path exists and does not need to be cleaned
                return

            shutil.rmtree(self.path)
        os.makedirs(self.path)

        # else clean it?


    def list_files(self, prefix):
        """List files with given prefix

        Args:
            object_name: Name of object to download from S3 (filename)
        Returns:
            list of objects
        """
        return [{
            "filename": prefix+"/test.file",
            "lastModified": 1643353661,
            "size": 0
        }]

    def get_object_tags(self, object_key: str):
        """Get tags of a S3 object
        Args:
            object_key: key for the S3 File
        Returns:
           List of key value pairs of tags if configured
           Empty list for an object with no tags
        """
        print(f'mock get_object_tags  for {object_key}')
        return [
                {"Key": f"{self.bucket_name}_1", "Value": f"{object_key}_1"},
                {"Key": f"{self.bucket_name}_2", "Value": f"{object_key}_2"}
               ]

    def update_object_tags(self, object_key: str, new_tags: dict, merge: bool):
        """Update tags for an object
        Args:
            object_key: key for the S3 File
            new_tags: dictionary of tags to set to the s3 object
            merge: true if the requested tags be merged with existing tags
        Returns:
            List of tags in form of dictionary with key value pairs
        """
        new_tags = new_tags or {}
        existing = self.get_object_tags(object_key)
        print(f"found existing tags {existing} for object {object_key}")
        if merge:
            # merge existing with new tags
            existing = {item['Key']: item['Value'] for item in existing}
            existing.update(new_tags)
            final_tags = [{'Key': key, 'Value': existing.get(key)} for key in existing]
        else:
            # replace existing with new tags
            final_tags = [{'Key': key, 'Value': new_tags.get(key)} for key in new_tags]
        print(f"replacing them with new tags {final_tags}")
        print(f'mock update_object_tags done for {object_key},'
              f' new tags {new_tags},'
              f' merge {merge},'
              f' bucket {self.bucket_name}')
        return final_tags

    def download_folder(self, folder_name: str,
                        location: str,
                        skip_download: any = None,
                        filter_data: dict = None,
                        ):
        """ Download a folder recursively to a given base location
        Note that you can have the bucket created with accelerated upload/download enabled
        and then provide config in settings to use the accelerated end points
        (40-60% faster)
        Includes functionality to skip download of a file, implementation provided by the caller
        Example use - download of a SimPro model which contains several files in diff sub-folders
        Args:
            folder_name: Name of prefix to download from S3 .e.g bearing_select_double
            location: Location to store the downloaded files.
                    e.g /localhome/templates/bearing_select_double
            skip_download: method provided by client to skip download of file or not.
                          invoked for each object key and accepts 2 args
                         - object key: strand object last modified at: datetime
            filter_data: dict of files metadata. key: file_key,
                            value as : datetime in str format.
        Returns:
            dictionary of all files in prefix, key as the file key,
            value as the last modified (datetime) object
        """

        print(f'download files from bucket {self.bucket_name} for'
              f' prefix {folder_name} '
              f'to location {location}')
        targets = {}
        filtered = [S3Object('/model/object_key_1'),
                    S3Object('/model/object_key_2'),
                    S3Object('/model/object_key_3')]
        for obj in filtered:
            key = obj.key
            targets.update({key: obj.last_modified})
            # caller's provided method invoked
            if (skip_download is not None
                    and skip_download(key, obj.last_modified, filter_data)):
                continue
            target = os.path.join(location, os.path.relpath(key, folder_name))
            if key[-1] == '/':
                continue
            print(f'  downloading {key} to {target}')
        return targets


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
        raise ItemNotFound(message)

# pylint: disable=too-few-public-methods
class S3Object:
    """Simple mock S3 object to test"""
    def __init__(self, key):
        """Constructor"""
        self.key = key
        # random generate last modified time
        self.last_modified = datetime.datetime(2023,
                                               12,
                                               11, 8,
                                               24,
                                               random.randint(0, 59),
                                               tzinfo=datetime.timezone.utc)
