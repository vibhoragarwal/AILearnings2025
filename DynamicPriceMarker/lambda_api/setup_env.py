"""Environment setup for lambda (in this folder)

Include this file in the lambda main file to setup the proper environment
"""
import glob
import json
import logging
import os


from dotenv import load_dotenv

load_dotenv()

from foundation.aws_lambda.bearingdatabase import BearingDatabase
from foundation.aws_lambda.s3 import S3Wrapper
from foundation.aws_lambda.sns import SNSWrapper
from foundation.aws_lambda.sqs import SQSWrapper
from foundation.stub.mockdatabase import MockDatabase
from foundation.stub.mocks3 import MockS3Wrapper
from foundation.stub.mocksns import MockSNS
from foundation.stub.mocksqs import MockSQS
from foundation.utils.featurebroker import FeatureBroker

# Get log level from environment variable
SERVICE_NAME = "dynamic-price-marker"
FeatureBroker.register("ServiceName", SERVICE_NAME)
mock = os.environ.get("NEST_MOCK", [])
if mock in ["all", "aws"]:
    # At this moment, all we can mock are also AWS services
    mock = ["s3", "dynamodb", "sqs", "eventbridge", "sns", "athena", "stepfunctions"]


if "NEST_VERSION" in os.environ:
    print("Starting " + SERVICE_NAME + ": " + os.environ["NEST_VERSION"])
else:
    print(f"Missing environment for {SERVICE_NAME} NEST_VERSION - using default")
    os.environ["NEST_VERSION"] = "0.0.1"

loglevel_string = os.environ.get("LOGLEVEL")
if loglevel_string:
    print(f"Got LOGLEVEL ({loglevel_string}) from env")
    root = logging.getLogger()
    default_level = root.getEffectiveLevel()
    print(f"Default loglevel number: {default_level}")
    loglevel_num = getattr(logging, loglevel_string.upper(), default_level)
    print(f"New loglevel number: {loglevel_num}")
    if loglevel_num != default_level:
        print(f"Changing log level from {default_level} to {loglevel_num}")
        logging.basicConfig(level=loglevel_num)
        if root.handlers:
            for handler in root.handlers:
                root.setLevel(loglevel_num)

user = os.environ.get("USER", "jenkins")


def configure_spark_for_s3():
    # Define S3 Paths
    # Notice we use 's3a://' instead of 'os.path.join' for local folders
  # hadoop-aws allows Spark to use 's3a://'
    hadoop_s3_path = f"s3a://{FeatureBroker.Bucket}"

    raw_market_alerts_path = "ingestion/raw_market_alerts/"
    bronze_market_history_path = "ingestion/bronze_market_history/"
    bronze_checkpoint_path = "ingestion/checkpoints/bronze/"
    silver_checkpoint_path = "ingestion/checkpoints/silver/"
    silver_market_prices_path = "ingestion/silver_market_prices/"
    gold_pricing_decisions_path = "ingestion/gold_pricing_decisions/"

    FeatureBroker.register("raw_market_alerts_path",  os.path.join(hadoop_s3_path, raw_market_alerts_path))
    FeatureBroker.register("bronze_market_history_path", os.path.join(hadoop_s3_path, bronze_market_history_path))
    FeatureBroker.register("bronze_checkpoint_path", os.path.join(hadoop_s3_path, bronze_checkpoint_path))
    FeatureBroker.register("silver_checkpoint_path", os.path.join(hadoop_s3_path, silver_checkpoint_path))
    FeatureBroker.register("silver_market_prices_path", os.path.join(hadoop_s3_path, silver_market_prices_path))
    FeatureBroker.register("gold_pricing_decisions_path", os.path.join(hadoop_s3_path, gold_pricing_decisions_path))


    FeatureBroker.S3.create_s3_folder(raw_market_alerts_path)
    FeatureBroker.S3.create_s3_folder(bronze_market_history_path)
    FeatureBroker.S3.create_s3_folder(bronze_checkpoint_path)
    FeatureBroker.S3.create_s3_folder(silver_checkpoint_path)
    FeatureBroker.S3.create_s3_folder(silver_market_prices_path)
    FeatureBroker.S3.create_s3_folder(gold_pricing_decisions_path)

def setup_is_databricks():
    is_databricks = "DATABRICKS_RUNTIME_VERSION" in os.environ
    FeatureBroker.register("DataBricks", is_databricks)

def setup_s3():
    """Setup S3 storage location"""
    # pylint: disable=invalid-name

    if "s3" in mock:
        print("Using MOCK S3")
        s3 = MockS3Wrapper(
            {
                "bucket": os.environ.get(
                    "NEST_OUTPUT_BUCKET", "va-databricks-learn-1"
                ),
                "path": os.environ.get("NEST_MOCK_S3_PATH", "/tmp/s3"),
                "container_id": os.environ.get("NEST_CONTAINER_ID", ""),
            }
        )
    else:
        s3_bucket = os.environ.get("NEST_OUTPUT_BUCKET", "va-databricks-learn-1")
        print("Using S3: ", s3_bucket)
        s3 = S3Wrapper({"bucket": s3_bucket})
        FeatureBroker.register("Bucket", s3_bucket)
    FeatureBroker.register("S3", s3)


def setup_sns():
    """Setup SNS"""
    # pylint: disable=invalid-name

    if "sns" in mock:
        print("Using MOCK SNS")
        sns = MockSNS({"topic": "mock_topic"})
    else:
        sns_topic = os.environ.get("NEST_SNS_TOPIC", "esod-bearing-optimizer-sns-topic-jenkins-dev")
        print("Using SNS topic: ", sns_topic)
        sns = SNSWrapper({"topic": sns_topic})
    FeatureBroker.register("SNS", sns)


def setup_bearing_db():
    """initialize bearing database for lookup for bearing data"""
    if "dynamodb" in mock or os.environ.get("NEST_MOCK_BEARING_DB", "false").lower() == "true":
        print("Using MOCK Bearing Database! ")

        target_folder = os.path.join(os.environ.get("NEST_MODEL_DIR", '..'), 'integration_test', 'bearings')
        if not os.path.exists(target_folder):
            target_folder = os.path.join('.', 'integration_test', 'bearings')
        with open(os.path.join(target_folder, '6309.json'), encoding='UTF-8') as json_file:
            # JSON dict test data read from file
            test_data = json.load(json_file)
        database2 = MockDatabase("bearingdb", "6309", test_data)

        # Now add the remaining files as well

        for filename in glob.glob(os.path.join(target_folder, "*.json")):
            with open(os.path.join(filename), encoding='UTF-8') as json_file:
                bearing = json.load(json_file)
            if bearing["designation"] == "6309":
                continue
            if "id" not in bearing:
                bearing["id"] = bearing["designation"]
            database2.store(bearing)
    else:
        dbname = os.environ.get('NEST_BEARING_DB_NAME', 'esod-bearingselect-db-dev')
        print(f'bearing select db {dbname}')
        database2 = BearingDatabase({'dbname': dbname})

    FeatureBroker.register("BearingDB", database2)
    FeatureBroker.register("User", "testUser")


def setup_sqs():
    """Setup queue configuration"""

    def create_sqs():
        """Create SQSWrapper object for
        model & direct clusters, for the
        2 versions to eb supported - released and latest
        Args:
            None
        Returns:
            SQSWrapper
        """
        queue_url = os.environ.get(
            "NEST_SQS_OPTIMIZER_ANALYTICS_URL",
            os.environ.get(
                "NEST_SQS_OPTIMIZER_ANALYTICS_NAME",
                "esod-bearing-optimizer-analytics-jenkins-dev.fifo",
            ),
        )
        return SQSWrapper(
            {
                "queue_url": queue_url,
                "messageGroupId": "esod_bearing_optimizer_api"
            }
        )

    if "sqs" in mock or os.environ.get("NEST_MOCK_SQS", "false").lower() == "true":
        print("Using MOCK SQS")

        mocked_queue = MockSQS(
            {
                "queue_url": "sqs://mock.me/sqs_mock_analytics",
                "container_id": os.environ.get("NEST_CONTAINER_ID", ""),
                "path": os.environ.get("NEST_MOCK_SQS_FOLDER", ""),
            }
        )
        FeatureBroker.register("AnalyticsQueue", mocked_queue)

    else:
        actual_queue = create_sqs()
        FeatureBroker.register("AnalyticsQueue", actual_queue)



def setup_download_analytics_sqs():
    """Setup queue configuration"""

    def create_sqs():
        """Create SQSWrapper object
        Args:
            None
        Returns:
            SQSWrapper
        """
        queue_url = os.environ.get(
            "NEST_SQS_OPTIMIZER_DOWNLOAD_ANALYTICS_URL",
            os.environ.get(
                "NEST_SQS_OPTIMIZER_DOWNLOAD_ANALYTICS_NAME",
                "esod-bearing-optimizer-download-analytics-jenkins-dev",
            ),
        )
        return SQSWrapper(
            {
                "queue_url": queue_url,
                "messageGroupId": "esod_bearing_optimizer_api"
            }
        )

    if "sqs" in mock or os.environ.get("NEST_MOCK_SQS", "false").lower() == "true":
        print("Using MOCK SQS")

        mocked_queue = MockSQS(
            {
                "queue_url": "sqs://mock.me/sqs_mock_download_analytics",
                "container_id": os.environ.get("NEST_CONTAINER_ID", ""),
                "path": os.environ.get("NEST_MOCK_SQS_FOLDER", ""),
            }
        )
        FeatureBroker.register("DownloadAnalyticsQueue", mocked_queue)

    else:
        actual_queue = create_sqs()
        FeatureBroker.register("DownloadAnalyticsQueue", actual_queue)

def update_environment():
    """ set up the env

    Returns:
        nothing
    """
    print("Initializing environment")
    setup_is_databricks()
    setup_s3()
    configure_spark_for_s3()