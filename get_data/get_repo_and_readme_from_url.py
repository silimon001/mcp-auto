import requests
import json
import os
import time
import logging
from dotenv import load_dotenv
import base64

from dataset_setting import dataset_name

load_dotenv('.mcp-auto_env')

# logging
os.makedirs("log_file", exist_ok=True)
logging.basicConfig(
    filename=f"log_file/get_data/get_repo_from_{dataset_name}.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

headers = {
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
    "Accept": "application/vnd.github.v3+json",
}

# 输入文件（每行一个 repo URL）
INPUT_FILE = f"data/dataset/{dataset_name}/link.log"

# 输出目录
OUTPUT_FILE = f"data/dataset/{dataset_name}/repo_info.json"
OUTPUT_FILE2 = f"data/dataset/{dataset_name}/repo_info.jsonl"
os.makedirs("data", exist_ok=True)

readme_dir = f"data/dataset/{dataset_name}/readme"
os.makedirs(readme_dir, exist_ok=True)


def parse_github_url(url: str):
    """
    从 https://github.com/owner/repo 提取 owner 和 repo
    """
    parts = url.strip().split("/")
    if len(parts) < 5:
        return None, None
    return parts[3], parts[4]


def get_repo_info(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Failed: {owner}/{repo} - {response.status_code}")
        return None

    data = response.json()

    # 提取关键字段
    return {
        "id": data.get('id'),
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "api_url": data.get("url"),
        "html_url": data.get("html_url"),
        "size": data.get("size"),
        "stars_count": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "watchers": data.get("watchers_count"),
        "language": data.get("language"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "url": data.get("html_url"),
        "topics": data.get("topics"),
        "license": data.get("license", {}).get("name") if data.get("license") else None
    }

def get_readme(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logging.warning(f"README not found: {owner}/{repo} - {response.status_code}")
        return None

    data = response.json()

    content = data.get("content")
    if not content:
        return None

    try:
        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
        return decoded
    except Exception as e:
        logging.error(f"Decode README failed: {owner}/{repo} - {e}")
        return None


def main():
    results = []

    with open(INPUT_FILE, "r") as f:
        repo_urls = f.readlines()

    for repo_url in repo_urls:
        owner, repo = parse_github_url(repo_url)

        if not owner:
            logging.warning(f"Invalid URL: {repo_url}")
            continue

        logging.info(f"Fetching {owner}/{repo}")
        info = get_repo_info(owner, repo)

        if info:
            results.append(info)

            # 获取 README
            readme_content = get_readme(owner, repo)

            if readme_content:
                safe_name = info["full_name"].replace("/", "_")
                filename = f"{info['id']}_{safe_name}_README.md"
                filepath = os.path.join(readme_dir, filename)

                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(readme_content)
                except Exception as e:
                    logging.error(f"Save README failed: {owner}/{repo} - {e}")

        time.sleep(1)  # 防止 rate limit

    # 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    with open(OUTPUT_FILE2, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item) + "\n")

    logging.info(f"Saved {len(results)} repos")


if __name__ == "__main__":
    main()