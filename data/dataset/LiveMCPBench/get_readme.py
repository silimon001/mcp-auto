import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = "data/dataset/LiveMCPBench/link.log"
OUTPUT_DIR = "data/dataset/LiveMCPBench/readme"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "Accept": "application/vnd.github.raw",
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"
}


def parse_github_url(url):
    """
    返回: owner, repo, branch, path
    """
    path = urlparse(url).path.strip("/")
    parts = path.split("/")

    if len(parts) < 2:
        return None, None, None, None

    owner = parts[0]
    repo = parts[1]

    branch = None
    sub_path = ""

    # 处理 tree URL
    if len(parts) > 2 and parts[2] == "tree":
        if len(parts) >= 4:
            branch = parts[3]
        if len(parts) > 4:
            sub_path = "/".join(parts[4:])

    return owner, repo, branch, sub_path


def fetch_readme_from_dir(owner, repo, path, branch):
    """
    从指定目录查找 README
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    params = {}
    if branch:
        params["ref"] = branch

    try:
        res = requests.get(api_url, headers=HEADERS, params=params, timeout=10)
        if res.status_code != 200:
            return None

        files = res.json()

        for f in files:
            name = f["name"].lower()
            if name.startswith("readme"):
                # 直接用 download_url
                download_url = f["download_url"]
                r = requests.get(download_url, timeout=10)
                if r.status_code == 200:
                    return r.text

    except Exception as e:
        print(f"[!] Dir fetch error: {owner}/{repo}/{path} -> {e}")

    return None


def fetch_root_readme(owner, repo):
    """
    获取根目录 README
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        print(f"[!] Root fetch error: {owner}/{repo} -> {e}")

    return None


def fetch_readme(owner, repo, branch, sub_path):
    """
    总调度逻辑
    """
    # 优先子目录
    if sub_path:
        content = fetch_readme_from_dir(owner, repo, sub_path, branch)
        if content:
            return content

    # fallback 到 root
    return fetch_root_readme(owner, repo)


def save_readme(owner, repo, sub_path, content):
    """
    文件命名：包含 path 防冲突
    """
    path_tag = sub_path.replace("/", "_") if sub_path else "root"
    filename = f"{owner}_{repo}_{path_tag}_README.md"

    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[+] Saved: {filepath}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        print(f"\nProcessing: {url}")

        owner, repo, branch, sub_path = parse_github_url(url)

        if not owner or not repo:
            print(f"[!] Invalid URL: {url}")
            continue

        content = fetch_readme(owner, repo, branch, sub_path)

        if content:
            save_readme(owner, repo, sub_path, content)
        else:
            print(f"[!] No README found: {owner}/{repo}/{sub_path}")


if __name__ == "__main__":
    main()