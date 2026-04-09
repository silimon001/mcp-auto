#!/usr/bin/env python3
"""
Batch fetch GitHub repository information and README files.

Usage:
    python fetch_github_repos.py --input repos.txt --output repos_info.json --readme-dir ./readmes

Input file format (one URL per line):
    https://github.com/owner/repo
    https://github.com/owner/repo.git
    github.com/owner/repo
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Extract owner and repository name from a GitHub URL.

    Supports formats:
        https://github.com/owner/repo
        https://github.com/owner/repo.git
        github.com/owner/repo
        git@github.com:owner/repo.git
    """
    # Remove trailing .git if present
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    # Extract pattern: owner/repo
    patterns = [
        r"github\.com[:/]([^/]+)/([^/]+)",  # https or ssh
        r"github\.com/([^/]+)/([^/]+)",     # plain
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            owner = match.group(1)
            repo = match.group(2)
            return owner, repo

    raise ValueError(f"Could not parse GitHub URL: {url}")


def github_request(
    endpoint: str, token: Optional[str] = None, accept_raw: bool = False
) -> Optional[requests.Response]:
    """Make a request to GitHub API with optional authentication."""
    url = f"https://api.github.com/{endpoint.lstrip('/')}"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    if accept_raw:
        headers["Accept"] = "application/vnd.github.raw+json"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response
    elif response.status_code == 404:
        # Repository or README not found
        return None
    else:
        print(f"  API error {response.status_code}: {response.text[:200]}")
        response.raise_for_status()
        return None  # unreachable if raise


def get_repo_info(owner: str, repo: str, token: Optional[str] = None) -> Optional[Dict]:
    """Fetch repository information from GitHub API."""
    resp = github_request(f"repos/{owner}/{repo}", token=token)
    if resp is None:
        print(f"  Repository {owner}/{repo} not found or inaccessible")
        return None
    data = resp.json()

    # Extract desired fields
    info = {
        "id": data.get("id"),
        "name": data.get("name"),
        "full_name": data.get("full_name"),
        "owner": data.get("owner", {}).get("login"),
        "description": data.get("description"),
        "html_url": data.get("html_url"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "license": data.get("license", {}).get("name") if data.get("license") else None,
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "language": data.get("language"),
    }
    return info


def get_readme(
    owner: str, repo: str, token: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch README content and its file extension.

    Returns:
        (content, extension) where extension is like '.md', '.rst', '.txt' or None.
        content is None if README not found.
    """
    # First get metadata to know the file name (for extension)
    resp_meta = github_request(f"repos/{owner}/{repo}/readme", token=token)
    if resp_meta is None:
        return None, None

    meta = resp_meta.json()
    # Get download URL or use raw content via Accept header
    download_url = meta.get("download_url")
    if download_url:
        # Download raw content
        try:
            resp_raw = requests.get(download_url)
            if resp_raw.status_code == 200:
                content = resp_raw.text
                # Determine extension from file name
                name = meta.get("name", "README")
                ext = os.path.splitext(name)[1]
                return content, ext
        except Exception as e:
            print(f"  Failed to download README from {download_url}: {e}")

    # Fallback: use API with raw Accept header
    resp_raw = github_request(
        f"repos/{owner}/{repo}/readme", token=token, accept_raw=True
    )
    if resp_raw is not None:
        content = resp_raw.text
        # Try to infer extension from content-type? default to .md
        ext = ".md"  # assume markdown
        return content, ext

    return None, None


def main():
    from dotenv import load_dotenv
    load_dotenv('.mcp-auto_env')
    parser = argparse.ArgumentParser(
        description="Fetch GitHub repository info and README files."
    )
    parser.add_argument(
        "--input", "-i", default="/home/silimon/mcp-auto/data/dataset/MCP-Bench/link.log", help="File containing list of repository URLs"
    )
    parser.add_argument(
        "--output", "-o", default="/home/silimon/mcp-auto/data/dataset/MCP-Bench/repo_info.json", help="Output JSON file"
    )
    parser.add_argument(
        "--readme-dir",
        "-d",
        default="/home/silimon/mcp-auto/data/dataset/MCP-Bench/readme",
        help="Directory to save README files (created if not exists)",
    )
    parser.add_argument(
        "--token", "-t", default=os.getenv('GITHUB_TOKEN'), help="GitHub personal access token (optional, increases rate limit)"
    )
    args = parser.parse_args()

    # Read input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Found {len(urls)} repository URLs")

    # Prepare output directory for READMEs
    readme_dir = Path(args.readme_dir)
    readme_dir.mkdir(parents=True, exist_ok=True)

    all_repos = []
    for idx, url in enumerate(urls, 1):
        print(f"\n[{idx}/{len(urls)}] Processing: {url}")
        try:
            owner, repo = parse_github_url(url)
        except ValueError as e:
            print(f"  Error: {e}")
            continue

        # Fetch basic info
        info = get_repo_info(owner, repo, token=args.token)
        if info is None:
            continue

        # Fetch README
        readme_content, _ = get_readme(owner, repo, token=args.token)  # ignore original extension
        readme_filename = None
        readme_path = None
        if readme_content:
            # New naming convention: {id}_{owner}_{name}_README.md
            readme_filename = f"{info['id']}_{info['owner']}_{info['name']}_README.md"
            readme_path = readme_dir / readme_filename
            with open(readme_path, "w", encoding="utf-8") as rf:
                rf.write(readme_content)
            print(f"  Saved README -> {readme_path}")
        else:
            print("  No README found")

        # Add README file reference to info
        info["readme_file"] = str(readme_path) if readme_path else None
        all_repos.append(info)

    # Write all info to JSON
    with open(args.output, "w", encoding="utf-8") as jf:
        json.dump(all_repos, jf, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved {len(all_repos)} repositories' info to {args.output}")
    print(f"README files saved in {readme_dir}")


if __name__ == "__main__":
    main()