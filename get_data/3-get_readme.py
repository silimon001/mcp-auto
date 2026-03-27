import requests
import json
import os
import time
import base64
from glob import glob
import logging
from dotenv import load_dotenv
import json
from typing import List, Dict

# load .env file
load_dotenv('.mcp-auto_env')

# set logfile
os.makedirs("log_file", exist_ok=True)
os.makedirs("log_file/get_data", exist_ok=True)

from datetime import datetime
now_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

logging.basicConfig(
    filename=f"log_file/get_data/get_readmes_{now_time}.log",
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

logging.info("Running")

raw_repos_info_path = "data/raw_repos_info/raw_repos_info.jsonl"
dataset_path = "data/dataset"

def get_repo_info(
    language: List[str] = ['py', 'js/ts'],
    stars: List[int] = [-1, -1],
    size: List[int] = [-1, -1],
) -> List[Dict]:
    input_file = raw_repos_info_path

    def language_match(repo_lang: str) -> bool:
        if repo_lang is None:
            return False
        repo_lang = repo_lang.lower()
        if 'py' in language and repo_lang == 'python':
            return True
        if 'js/ts' in language and repo_lang in ('javascript', 'typescript'):
            return True
        return False

    def range_match(value: int, min_max: List[int]) -> bool:
        min_v, max_v = min_max
        if min_v > -1 and value < min_v:
            return False
        if max_v > -1 and value > max_v:
            return False
        return True

    results: List[Dict] = []

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            repo = json.loads(line)

            if not language_match(repo.get("language")):
                continue

            if not range_match(repo.get("stars_count", 0), stars):
                continue

            if not range_match(repo.get("size", 0), [size[0]*1024, size[1]*1024]):
                continue

            results.append({
                "id": repo["id"],
                "full_name": repo["full_name"],
                "description": repo["description"],
                "api_url": repo['api_url'],
                "html_url": repo["html_url"],
                "language": repo["language"],
                "size": repo["size"],
                "stars_count": repo["stars_count"],
                "forks_count": repo["forks_count"],
                "open_issues_count": repo["open_issues_count"],
                "license": repo['license'],
                "topics": repo["topics"],
                "created_at": repo["created_at"],
                "updated_at": repo["updated_at"],
                "pushed_at": repo["pushed_at"],
                "owner": repo["owner"],
            })

    return results

def merge_repo_info(language: str, stars: list, size: list):

    data = get_repo_info(language, stars, size)
    
    print(language + " & " + str(stars[0]) + "," + str(stars[1]) + " & " + str(size[0]) + "," + str(size[1]) + ": ")
    print(type(data), len(data))
    
    parts = []

    # language
    if 'py' in language:
        parts.append('py')
    if 'js/ts' in language:
        parts.append('js_ts')

    # stars
    stars_str = 'stars'
    if stars[0] != -1:
        stars_str += f'_{stars[0]}'
    if stars[1] != -1:
        stars_str += f'_{stars[1]}'
    if len(stars_str) > 5:
        parts.append(stars_str)

    # size
    size_str = 'size'
    if size[0] != -1:
        size_str += f'_{size[0]}'
    if size[1] != -1:
        size_str += f'_{size[1]}'
    if len(size_str) > 4:
        parts.append(size_str)

    # link
    dir = dataset_path + "/" + '_'.join(parts)
    os.makedirs(dir, exist_ok=True)
    with open(dir + '/repo_info.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    with open(dir + '/repo_info.jsonl', 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item) + "\n")

def get_readme(language: str, stars: list, size: list):

    parts = []

    # language
    if 'py' in language:
        parts.append('py')
    if 'js/ts' in language:
        parts.append('js_ts')

    # stars
    stars_str = 'stars'
    if stars[0] != -1:
        stars_str += f'_{stars[0]}'
    if stars[1] != -1:
        stars_str += f'_{stars[1]}'
    if len(stars_str) > 5:
        parts.append(stars_str)

    # size
    size_str = 'size'
    if size[0] != -1:
        size_str += f'_{size[0]}'
    if size[1] != -1:
        size_str += f'_{size[1]}'
    if len(size_str) > 4:
        parts.append(size_str)

    # link
    dir = dataset_path + "/" + '_'.join(parts)

    os.makedirs(dir + '/readme', exist_ok=True)
    readme_files = glob(os.path.join(dir + "/readme", "*.md"))
    all_id = [os.path.basename(f).split('_')[0] for f in readme_files]

    counts = len(readme_files)
    logging.info(f"already got {counts} README files, ready to get the other...")

    headers = {
        "Authorization" : f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json",
    }

    # get API limit info
    response = requests.get("https://api.github.com/rate_limit", headers=headers)
    logging.info(f"GitHub API limit: {response.json()}")

    with open(f"{dir}/repo_info.json", "r", encoding="utf-8") as f:
        data: List[Dict] = json.load(f)

    # ---------------- main loop ---------------- #
    for repo in data:
        repo_id = str(repo.get("id"))
        repo_name = repo.get("full_name")

        if repo_id in all_id:
            logging.info(f"✅ {repo_name}'s Readme is existed. Skip.")
            continue

        counts += 1
        time.sleep(0.1)

        readme_url = repo.get("api_url") + "/readme"
        content = ""

        try:
            readme_response = requests.get(readme_url, headers=headers)
        except Exception as e:
            logging.error(f"Post {readme_url} error: {e}, wait 10s to retry.")
            time.sleep(10)
            readme_response = requests.get(readme_url, headers=headers)

        if readme_response.status_code == 200:
            content = readme_response.json().get("content", "")
            encoding = readme_response.json().get("encoding", "")

            if encoding == "base64":
                try:
                    content = base64.b64decode(content).decode("utf-8")
                except Exception as e:
                    logging.warning(f"⚠️ decoding error {repo.get('api_url')}: {e}")
                    continue
            else:
                # if the Readme file' size over 1 MB, this error will occur.
                logging.warning(f"⚠️ unkown encoding {repo.get('api_url')}: {encoding}")
                continue
        else:
            # if this repo hasn't Readme file, this error will occur.
            logging.error(f"❌ Error code: {readme_response.status_code} {repo_name}")
            continue

        filename = dir + f"/readme/{repo_id}_{repo_name.split('/')[1]}_README.md"
        with open(filename, "w", encoding="utf-8", newline='\n') as f:
            f.write(content)

        logging.info(f"✅ already saved {repo_name}'s Readme to {filename}")



# stars_list = [[0,1], [1, 10], [10, 100], [100, -1]]
stars_list = [[-1, -1]]
sizes_list = [[-1,-1]]
for stars in stars_list:
    for sizes in sizes_list:
        for language in ['py', 'js/ts']:
            merge_repo_info(language, stars, sizes)
            get_readme(language, stars, sizes)
