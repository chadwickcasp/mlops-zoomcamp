import json
import uuid
from datetime import datetime
from time import sleep, time

import pyarrow.parquet as pq
import requests

print("Reading parquet file...")
start_read = time()
table = pq.read_table("green_tripdata_2022-01.parquet")
data = table.to_pylist()
read_time = time() - start_read
print(f"✓ File read completed in {read_time:.3f}s ({len(data)} rows)")


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


with open("target.csv", 'w') as f_target:
    total_start = time()
    for idx, row in enumerate(data, 1):
        row_start = time()
        
        # Row processing
        process_start = time()
        row['id'] = str(uuid.uuid4())
        duration = (row['lpep_dropoff_datetime'] - row['lpep_pickup_datetime']).total_seconds() / 60
        process_time = time() - process_start
        
        # File writing
        write_start = time()
        if duration != 0.0:
            f_target.write(f"{row['id']},{duration}\n")
        write_time = time() - write_start
        
        # JSON serialization
        json_start = time()
        json_data = json.dumps(row, cls=DateTimeEncoder)
        json_time = time() - json_start
        
        # HTTP request
        http_start = time()
        resp = requests.post("http://127.0.0.1:9696/predict",
                             headers={"Content-Type": "application/json"},
                             data=json_data)
        http_time = time() - http_start
        
        # JSON deserialization
        parse_start = time()
        resp_json = resp.json()
        parse_time = time() - parse_start
        
        # Sleep
        sleep_start = time()
        sleep(1)
        sleep_time = time() - sleep_start
        
        row_time = time() - row_start
        
        # Print timing summary
        print(f"[Row {idx}/{len(data)}] prediction: {resp_json['duration']:.2f} | "
              f"Total: {row_time:.3f}s | "
              f"Process: {process_time*1000:.1f}ms | "
              f"Write: {write_time*1000:.1f}ms | "
              f"JSON: {json_time*1000:.1f}ms | "
              f"HTTP: {http_time:.3f}s | "
              f"Parse: {parse_time*1000:.1f}ms | "
              f"Sleep: {sleep_time:.3f}s")
    
    total_time = time() - total_start
    print(f"\n✓ All rows processed in {total_time:.2f}s (avg: {total_time/len(data):.3f}s per row)")
