import json
import os
import time
from datetime import datetime

# Path must match your 'input_path'
input_path = "../../ingestion/raw_market_alerts"


def generate_alert(item, comp, price):
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
generate_alert("Milk", "Market_A", 3.19)
time.sleep(2)
generate_alert("Bread", "Market_B", 2.11)