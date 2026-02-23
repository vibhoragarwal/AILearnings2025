from foundation.utils.featurebroker import FeatureBroker
from lambda_api.setup_env import update_environment
update_environment()

# Path must match your 'input_path'
input_path = "../../ingestion/raw_market_alerts"


import json
import time
import os
from datetime import datetime


def generate_alert(item, comp, price):
    file_name = f"alert_{item}_{int(time.time())}.json"
    # The full path in S3
    base_path = "ingestion/raw_market_alerts"
    s3_key = f"{base_path}/{file_name}"

    data = {
        "item_name": item,
        "competitor_name": comp,
        "competitor_price": float(price),
        "timestamp": datetime.now().isoformat()
    }

    FeatureBroker.S3.upload_data(json.dumps(data), s3_key)

    print(f"Uploaded to S3: {s3_key}")


def generate_local_alert(item, comp, price):
    file_name = f"alert_{item}_{int(time.time())}.json"
    data = {
        "item_name": item,
        "competitor_name": comp,
        "competitor_price": float(price),
        "timestamp": datetime.now().isoformat()
    }

    with open(os.path.join(input_path, file_name), 'w') as f:
        json.dump(data, f)
    print(f"Generated: {file_name}")


# Simulate a few alerts
generate_alert("Milk", "Market_A", 2.11)
time.sleep(2)
generate_alert("Bread", "Market_B", 3.19)
time.sleep(2)
generate_alert("Butter", "Market_A", 43.19)