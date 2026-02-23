import json
import os
import time
from datetime import datetime

from DynamicPriceMarker.config.s3 import get_s3_client, RAW_MARKET_ALERTS_PREFIX, BUCKET_NAME

# Path must match your 'input_path'
input_path = "../../ingestion/raw_market_alerts"


import json
import time
import os
from datetime import datetime


def generate_alert(item, comp, price):
    file_name = f"alert_{item}_{int(time.time())}.json"
    # The full path in S3
    s3_key = f"{RAW_MARKET_ALERTS_PREFIX}/{file_name}"

    data = {
        "item_name": item,
        "competitor_name": comp,
        "competitor_price": float(price),
        "timestamp": datetime.now().isoformat()
    }

    # Convert dict to JSON string and upload
    get_s3_client().put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=json.dumps(data),
        ContentType='application/json'
    )
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
generate_alert("Milk", "Market_A", 3.11)
time.sleep(2)
generate_alert("Bread", "Market_B", 2.19)