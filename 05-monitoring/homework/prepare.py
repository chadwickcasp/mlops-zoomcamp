from tqdm import tqdm
import requests

files = ["green_tripdata_2021-03.parquet", "green_tripdata_2021-04.parquet", "green_tripdata_2021-05.parquet"]
path = "./datasets"
print(f"Download files:")
for file in files:

    # Change the url based on what works for you whether s3 or cloudfront
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{file}"
    # url = f"https://nyc-tlc.s3.amazonaws.com/trip+data/{file}"
    # Added User-Agent header to avoid WAF challenges
    resp = requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
    save_path = f"{path}/{file}"
    with open(save_path, "wb") as handle:
        for data in tqdm(resp.iter_content(),
                         desc=f"{file}",
                         postfix=f"save to {save_path}",
                         total=int(resp.headers["Content-Length"])):
            handle.write(data)
