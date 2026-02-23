""" Simple S3 interface, designed accoring to YAGNI principle

Only build stuff that I need at the time that I need it

Uses NEST_S3_BUCKET to identify the bucket if no bucket is given while creating the wrapper

"""

import os
import logging
import time
from typing import Optional
import hashlib
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from foundation.utils.customexceptions import ItemNotFound, ConfigurationError, ActionNotAllowed
from foundation.utils.utils import log_time_spend


logger = logging.getLogger("nest.s3")

# pylint: disable=raise-missing-from

def s3_exception(func):
    """Wraps a function to provide uniform exception handling for boto3 exceptions"""

    def wrapper(self, *args, **kwargs):
        try:
            # This is a check to see if the resource actually exists
            return func(self, *args, **kwargs)
        except ClientError as client_error:
            if client_error.response["Error"]["Code"] == "NoSuchKey":
                raise ItemNotFound(client_error.response["Error"]["Key"])
            if client_error.response["Error"]["Code"] == "AccessDenied":
                print(self.bucket_name)
                raise ActionNotAllowed(self.bucket_name)
            if client_error.response["Error"]["Code"] in (
                "NoSuchBucket",
                "InvalidBucketName",
            ):
                print(self.bucket_name)
                raise ConfigurationError(self.bucket_name, "No Access to resource")
            # Other errors are not handled yet:
            # InvalidObjectState, InvalidRange, InternalError, ServiceUnavailable, SlowDown
            # RequestTimeout, PreconditionFailed, InvalidPart, InvalidPartOrder, EntityTooSmall
            # EntityTooLarge, ExpiredToken, SignatureDoesNotMatch, BadRequest
            logger.exception("Exception while calling S3 operation:")
            raise ConfigurationError(
                self.bucket_name, "Generic error"
            ) from client_error

    return wrapper


def compute_etag(file_path):
    """Compute ETag for a file S3 style - but will prabably not be correct"""
    md5_hash = hashlib.md5()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            md5_hash.update(chunk)

    return md5_hash.hexdigest()


# pylint: disable=raise-missing-from
class S3Wrapper:
    """
    Generic database wrapper for AWSs DynamoDB
    @ingroup aws_lambda
    """

    s3_client_instance = None
    s3_resource_instance = None

    def __init__(self, settings):
        """Constructor for the database
        Args:
            settings: containing the configuration options to connect to the database
        """
        self.settings = settings
        self.bucket_name = self.settings.get("bucket", os.environ.get("NEST_S3_BUCKET"))
        self.signature_version = self.settings.get("signatureVersion") or "s3v4"
        self.config = self.settings.get("client_config")
        logger.info("Connecting to bucket %s", self.bucket_name)

    @property
    def s3_client(self):
        """S3 Property to use caching in lambda optimally"""
        if not S3Wrapper.s3_client_instance:
            config = Config(signature_version=self.signature_version)
            S3Wrapper.s3_client_instance = boto3.client("s3", config=config)
        return S3Wrapper.s3_client_instance

    @property
    def s3_resource(self):
        """S3 Property to use caching in lambda optimally"""
        if not S3Wrapper.s3_resource_instance:
            config = Config(signature_version=self.signature_version)
            S3Wrapper.s3_resource_instance = boto3.resource("s3", config=config)
        return S3Wrapper.s3_resource_instance

    # ####################################
    # Public methods - part of interface
    # ####################################

    @log_time_spend("s3-upload-data")
    @s3_exception
    def upload_data(self, source_data, target_name):
        """Upload data to the S3 bucket using target_name as key, and source_name as body.
        Data is either binary data or string. At this moment large file uploads are not
        yet supported. Please contact edwin if you need this feature.

        """
        # pylint: disable=no-member
        if len(source_data) > 5 * 1024 * 1024:
            logger.error("File too large to upload to S3 in one call")
            raise NotImplementedError(
                "multipart upload"
            )  # Use multipart upload for large files
            # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3.html#multipart-uploads
            # https
        if len(target_name) > 1024:
            logger.error("File name too large to upload to S3")
            raise ValueError("File name too large to upload to S3")

        bucket = self.s3_resource.Bucket(self.bucket_name)
        put_data = {
            "Body": source_data,
            "Key": target_name,
            "Tagging": "purpose=testing",
        }
        s3_object = bucket.put_object(**put_data)
        print(s3_object.bucket_name)
        print(s3_object.key)

    @s3_exception
    def upload_zip_file(self, source_zip_path, zip_file_name, target_s3_bucket):
        """Test if the database is accessible right now
        Returns:
            True if database is accessible, False otherwise
        """
        if len(zip_file_name) > 1024:
            logger.error("File name too large to upload to S3: %s", zip_file_name)
            raise ValueError("File name too large to upload to S3")

        self.s3_resource.meta.client.upload_file(
            source_zip_path, self.bucket_name, target_s3_bucket + "/" + zip_file_name
        )

    def upload_to_unique_file(
        self, source_data, base_name, extension, folder_name=None
    ):
        """Uploads source data to s3 and generated a unique filename"""
        filename = self.create_unique_filename(base_name, extension, folder_name)
        self.upload_data(source_data, filename)

    def upload_to_folder(self, source_data, folder_name, filename):
        """Uploads source data to s3 and generated a unique foldername if no foldername is given

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
        """Uploads source data to s3 and generated a unique foldername if no foldername is given

        foldername will be base_name/timeisms/
        use file path is then base_name/timeinms/filename

        Args:
            folder_name: parent folder name used to store filename in
            filename: the name that needs to be used to save the source_data in the unique folder

        """
        # Since we are not working on local OS, I do not use os.path tools
        # file_path = folder_name + "/" + filename
        self.upload_zip_file(source_zip_path, zip_file_name, target_s3_folder)

    @staticmethod
    def create_unique_filename(base_name, extension, folder_name=None):
        """filename = base_name + "_" + current_time + "." + extension"""
        current_time = int(round(time.time() * 1000))
        filename = f"{base_name}_{current_time}.{extension}"

        if folder_name:
            filename = folder_name + "/" + filename
        return filename

    @staticmethod
    def create_unique_foldername(base_name=None):
        """filename = base_name + "_" + current_time + "." + extension"""
        # Take current time in milliseconds. This should be enough uniqueness for 99.999% of the cases
        current_time = int(round(time.time() * 1000))
        if base_name:
            folder_name = f"{base_name}/{current_time}"
        else:
            folder_name = str(current_time)
        return folder_name

    @log_time_spend("s3-upload-file")
    @s3_exception
    def upload_file_to_s3(self, key, filepath):
        """Upload file to S3
        Returns:
            True if file is uploaded, False otherwise
        """
        try:
            self.s3_client.upload_file(
                Bucket=self.bucket_name, Key=key, Filename=filepath
            )
        except ClientError as client_error:
            print(
                f"Exception while uploading file {filepath} to S3 {self.bucket_name} with key {key}"
            )
            logging.error(client_error)
            raise
        return True

    @log_time_spend("s3-generateSigned-url")
    @s3_exception
    def generate_presigned_url(self, key, additional_params=None, is_read=True):
        """Method to generate signed URL
        Args:
            key: key to get S3 File
        Returns:
            Signed S3 URL
        """
        mode = "get_object" if is_read else "put_object"
        # signed_url = self.s3_client.generate_presigned_url(
        #     mode, Params={"Bucket": self.bucket_name, "Key": key}, ExpiresIn=3360
        # )

        if is_read and not self.does_key_exists(key):
            print(f"Report key {key} was not found, raising ItemNotFound exception")
            # do not send the key back to the user, its an internal formulation
            raise ItemNotFound("File key not found")

        params = {"Bucket": self.bucket_name, "Key": key}
        if additional_params:
            params.update(additional_params)
            print(f"using params {params}")

        signed_url = self.s3_client.generate_presigned_url(
            mode, Params=params, ExpiresIn=3360
        )
        print(signed_url)
        return signed_url

    @log_time_spend("s3-generate-presigned-post")
    def generate_presigned_post(
        self,
        object_name: str,
        fields: dict = None,
        conditions: list = None,
        expiration: int = 3360,
    ) -> Optional[dict]:
        """Generate a presigned URL S3 POST request to upload a file

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

        """
        # Generate a presigned S3 POST URL
        try:
            response = self.s3_client.generate_presigned_post(
                self.bucket_name,
                object_name,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration,
            )
        except ClientError as e:
            # Proably not the best thing you can do. Swallow eny error ...
            logging.error(e)
            return None

        # The response contains the presigned URL and required fields
        return response

    @log_time_spend("s3-does-key-exists")
    @s3_exception
    def does_key_exists(self, key):
        """Method to check if a key exists in s3
        Args:
            key: key for the S3 File
        Returns:
           True if key exists, else False
        """
        res = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name, Prefix=key, MaxKeys=1
        )
        return "Contents" in res

    @log_time_spend("s3-download-file")
    @s3_exception
    def download_file(self, object_name, location=None):
        """Download an object from S3 and store it in location

        Args:
            object_name: Name of object to download from S3 (filename)
            location: Location to store the downloaded file (None specified - /tmp will be used)
        Returns:
            path of downloaded file - of object_name only filename part is used
        """
        location = location or "/tmp/"
        target = os.path.join(location, os.path.basename(object_name))
        self.s3_client.download_file(self.bucket_name, object_name, target)
        return target

    @log_time_spend("s3-list_files")
    @s3_exception
    def list_files(self, prefix):
        """List files with given prefix

        Args:
            object_name: Name of object to download from S3 (filename)
            location: Location to store the downloaded file (None specified - /tmp will be used)
        Returns:
            List of dicts with "filename", "lastModified", "size" attributes
        """
        response = self.s3_client.list_objects(Bucket=self.bucket_name, Prefix=prefix)
        if not response.get("Contents"):
            return []
        result = [
            {
                "filename": item["Key"],
                "lastModified": item["LastModified"].timestamp(),
                "size": item["Size"],
            }
            for item in response["Contents"]
        ]

        return result

    @log_time_spend("s3-list_files")
    @s3_exception
    def list_root_files(self, prefix):
        """List files with given prefix and root folder

        Args:
            object_name: Name of object to download from S3 (filename)
            location: Location to store the downloaded file (None specified - /tmp will be used)
        Returns:
            List of dicts with "filename", "lastModified", "size" attributes
        """
        response = self.s3_client.list_objects(
            Bucket=self.bucket_name, Prefix=prefix, Delimiter="/"
        )
        if "CommonPrefixes" not in response:
            return []
        result = [obj["Prefix"] for obj in response["CommonPrefixes"]]
        return result

    @log_time_spend("s3-load-file")
    @s3_exception
    def load_file(self, filename, version_id=None):
        """Load an object from S3 and return its contents

        Args:
            object_name: Name of object to download from S3 (filename)
            location: Location to store the downloaded file (None specified - /tmp will be used)
        Returns:
            path of downloaded file - of object_name only filename part is used
        """
        if version_id:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=filename, VersionId=version_id
            )
        else:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=filename)
        return response["Body"].read()

    @log_time_spend("s3-get-object-tags")
    @s3_exception
    def get_object_tags(self, object_key: str):
        """Get tags of a S3 object
        Args:
            object_key: key for the S3 File
        Returns:
           List of key value pairs of tags if configured
           Empty list for an object with no tags
        """
        print(f"get_object_tags {object_key}")
        if not self.does_key_exists(object_key):
            raise ItemNotFound(object_key)
        response = self.s3_client.get_object_tagging(
            Bucket=self.bucket_name, Key=object_key
        )
        tag_set = response.get("TagSet", [])
        return tag_set

    @log_time_spend("s3-update-object-tags")
    @s3_exception
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
            existing = {item["Key"]: item["Value"] for item in existing}
            existing.update(new_tags)
            final_tags = [{"Key": key, "Value": existing.get(key)} for key in existing]
        else:
            # replace existing with new tags
            final_tags = [{"Key": key, "Value": existing.get(key)} for key in new_tags]
        print(f"replacing them with new tags {final_tags}")
        if len(final_tags) > 10:
            raise ConfigurationError(final_tags, "Number of tags cannot exceed 10")
        response = self.s3_client.put_object_tagging(
            Bucket=self.bucket_name, Key=object_key, Tagging={"TagSet": final_tags}
        )
        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            error_code = response["ResponseMetadata"]["HTTPStatusCode"]
            raise ActionNotAllowed(
                f"put_object_tagging for {object_key} in bucket {self.bucket_name}. Error code: {error_code}"
            )
        return final_tags

    @log_time_spend("s3-download-folder")
    @s3_exception
    def download_folder(
        self,
        folder_name: str,
        location: str,
        skip_download: any = None,
        filter_data: dict = None,
    ):
        """Download a folder recursively to a given base location
        Note that you can have the bucket created with accelerated upload/download enabled
        and then provide config in settings to use the accelerated end points
        (40-60% faster)
        Includes functionality to skip download of a file, implementation provided by the caller
        Example use - download of a SimPro model which contains several files in diff sub-folders
        Args:
            folder_name: Name of prefix to download from S3 .e.g bearing_select_double
            location: Location to store the downloaded files.
                    e.g /localhome/templates/bearing_select_double
            filter_data: method provided by client to skip download of file or not.
                          invoked for each object key and accepts 2 args
                         - object key: strand object last modified at: datetime
            files_metadata: dict of files metadata. key: file_key,
                            value as : datetime in str format.
        Returns:
            dictionary of all files in prefix, key as the file key,
            value as the last modified (datetime) object
        """
        # use accelerate end point if provided by client
        bucket = self.s3_resource.Bucket(self.bucket_name)
        print(
            f"download files from bucket {self.bucket_name} for"
            f" prefix {folder_name} "
            f"to location {location}"
        )
        targets = {}
        for obj in bucket.objects.filter(Prefix=folder_name):
            key = obj.key
            targets.update({key: obj.last_modified})
            # caller's provided method invoked
            if skip_download is not None and skip_download(
                key, obj.last_modified, filter_data
            ):
                continue
            target = os.path.join(location, os.path.relpath(key, folder_name))
            if not os.path.exists(os.path.dirname(target)):
                os.makedirs(os.path.dirname(target))
            if key[-1] == "/":
                continue

            print(f"  downloading {key} to {target}")
            bucket.download_file(key, target)
        return targets

    @log_time_spend("s3-create-folder")
    def create_s3_folder(self, folder_name):
        # In S3, a folder is just an empty object ending with '/'
        bucket = self.s3_resource.Bucket(self.bucket_name)
        if not folder_name.endswith('/'):
            folder_name += '/'
        bucket.put_object(Bucket=bucket, Key=folder_name)
        print(f"Created prefix: {folder_name} in {bucket}")

if __name__ == "__main__":
    # wrapper = S3Wrapper({"bucket": "test-bucket-edwin-s3"})
    # stringetje = json.dumps({"name": "The quick brown fix jumps over the lazy dog\n\n\nAnd sure he is lazy!\n"})
    # wrapper.upload_to_unique_file(stringetje, "compendium", "json", "de.UTF-8")
    wrapper = S3Wrapper({"bucket": "esod-simulation-upload-bucket-jenkins-dev"})
    wrapper.list_files("ZPRU-d363197a-e631-4fc8-96d7-bbcd19787bc")

    try:
        wrapper.load_file("I-do-not-exist.py")
    except ItemNotFound as e:

        print("As expected - item not found - nice")

    # Should have not access
    wrapper = S3Wrapper({"bucket": "esod-simulation-upload-bucket-test"})
    try:
        wrapper.load_file("I-do-not-exist.py")
    except ActionNotAllowed as e:

        print("As expected - Action not allowed - nice")

    wrapper = S3Wrapper({"bucket": "TheQuickBrownFox"})
    try:
        wrapper.load_file("I-do-not-exist.py")
    except ConfigurationError as e:

        print("As expected - Confiruation error - nice")
