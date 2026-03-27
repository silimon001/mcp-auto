import requests
import json
import os
import time
import sys
import logging
from dotenv import load_dotenv

# load .env file
load_dotenv('.mcp-auto_env')

# set logfile
os.makedirs("log_file", exist_ok=True)
os.makedirs("log_file/get_data", exist_ok=True)

from datetime import datetime
now_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

logging.basicConfig(
    filename=f"log_file/get_data/get_repos_{now_time}.log",
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("Running")

headers = {
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
    "Accept": "application/vnd.github.v3+json",
}

# GitHub API URL
url = "https://api.github.com/search/repositories"

try:
    response = requests.get("https://api.github.com/rate_limit", headers=headers)
    response.raise_for_status()
    logging.info(f"API rate limit: {response.json()}")
except Exception as e:
    logging.error(f"get rate limit failed: {e}")
    sys.exit(1)

# periods
time_periods = ["<2025-01-01",
                "2025-01-01..2025-01-31",
                "2025-02-01..2025-02-28",
                "2025-03-01..2025-03-31",
                "2025-04-01..2025-04-30",
                "2025-05-01..2025-05-31",
                "2025-06-01..2025-06-30",
                "2025-07-01..2025-07-31",
                "2025-08-01..2025-08-31",
                "2025-09-01..2025-09-30",
                "2025-10-01..2025-10-31",
                "2025-11-01..2025-11-30",
                "2025-12-01..2025-12-31",
                ]

logging.info(f"There are {len(time_periods)} periods.")

# mkdir
raw_dir = "data/raw"
os.makedirs(raw_dir, exist_ok=True)

# get repo info
for language in ['TypeScript', 'JavaScript', 'Python']:
    logging.info(f"Getting repo data, language type is {language}.")
    raw_dir_language = raw_dir + f"/{language}"
    os.makedirs(raw_dir_language, exist_ok=True)

    for time_period in time_periods:
        logging.info(f"repo data in {time_period} ...")
        counts = 1
        pages = 10
        while counts <= pages:
            time.sleep(2)

            params = {
                "q": f'"mcp server" in:name,description,readme language:{language} stars:>=10 created:{time_period}',
                "per_page": 100,
                "page": counts,
            }

            try:
                response = requests.get(url, params=params, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                elif response.status_code == 403:
                    logging.error("403 Forbidden.")
                    sys.exit(1)
                elif response.status_code == 422:
                    logging.error(f"422 Unprocessable Entity.")
                    sys.exit(1)
                else:
                    logging.error(f"Post failed, code: {response.status_code}, content: {response.text}")
                    sys.exit(1)
            except Exception as e:
                logging.error(f"Post error: {e}")
                sys.exit(1)

            total_count = data.get('total_count', 0)
            if total_count > 1000:
                logging.warning(f"Warning: The number of repo in {time_period} over 1000.")
                break
            else:
                pages = total_count // 100 + 1

            # filename
            if time_period == "<2017-01-01":
                filename = f"{raw_dir_language}/0000-00-00__2017-01-01__{counts}.json"
            else:
                filename = f"{raw_dir_language}/{time_period.replace('..', '__')}__{counts}.json"

            # save data
            try:
                with open(filename, "w", encoding="utf-8", newline='\n') as f:
                    json.dump(data, f, indent=2)
                logging.info(f"Saved to {filename}")
            except Exception as e:
                logging.error(f"Saving failed: {e}")

            counts += 1

logging.info("Over!")
