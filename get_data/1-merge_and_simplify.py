import json
import os
from glob import glob
from collections import Counter

def simplify_and_merge(data_dir: str, language):
    structured_data = []
    raw_repo_infos = glob(os.path.join(f"{data_dir}", "*.json"))

    os.makedirs(f"{data_dir}/raw_repos_info", exist_ok=True)

    seen_ids = set()
    seen_names = set()

    for raw_repo_info in raw_repo_infos:
        with open(raw_repo_info, 'r', encoding="utf-8") as f:
            data = json.load(f)
        for repo in data.get("items", []):
            repo_id = repo.get("id")
            repo_name = repo.get("full_name")

            # delete MCP-Mirror's MCP Server
            repo_org = repo["owner"]["login"]
            if repo_org == 'MCP-Mirror':
                print('1')
                continue

            unique_key = repo_id or repo_name
            if unique_key in seen_ids or unique_key in seen_names:
                # print(repo_id,repo_name)
                continue
            if repo_id:
                seen_ids.add(repo_id)
            else:
                seen_names.add(repo_name)

            structured_repo = {
                "id": repo_id,
                "full_name": repo_name,
                "description": repo.get("description"),
                "api_url": repo.get("url"),
                "html_url": repo.get("html_url"),
                "language": repo.get("language") or language,
                "size": repo.get("size"),
                "stars_count": repo.get("stargazers_count"),
                "forks_count": repo.get("forks_count"),
                "open_issues_count": repo.get("open_issues_count"),
                "license": repo["license"]["name"] if repo.get("license") else None,
                "topics": repo.get("topics", []),
                "created_at": repo.get("created_at"),
                "updated_at": repo.get("updated_at"),
                "pushed_at": repo.get("pushed_at"),
                "owner": {
                    "login": repo["owner"]["login"],
                    "id": repo["owner"]["id"],
                    "type": repo["owner"]["type"],
                },
            }
            structured_data.append(structured_repo)

    with open(f'{data_dir}/raw_repos_info/raw_repos_info.json', "w", encoding="utf-8", newline='\n') as f:
        json.dump(structured_data, f, indent=2)
    with open(f'{data_dir}/raw_repos_info/raw_repos_info.jsonl', "w", encoding="utf-8") as f:
        for item in structured_data:
            f.write(json.dumps(item) + "\n")

def load_json_objects(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = f.read().strip()
        try:
           
            objs = json.loads(data)
            if isinstance(objs, dict):
                objs = [objs]
        except json.JSONDecodeError:
            
            data = "[" + data.replace("}\n{", "},\n{") + "]"
            objs = json.loads(data)
    return objs

def count_owners(objs):
    owners = []
    for obj in objs:
        owner = obj.get("owner", {})
        login = owner.get("login")
        if login:
            owners.append(login)
    return Counter(owners)

def count_languages(objs):
    languages = []
    for obj in objs:
        language = obj.get("language")
        if language:
            languages.append(language)
        else:
            # print(obj.get('full_name'))
            languages.append('NULL')
    return Counter(languages)

if __name__ == "__main__":

    all_repos = []

    for language in ['TypeScript', 'JavaScript', 'Python']:
        data_dir = f"data/raw/{language}"
        simplify_and_merge(data_dir, language)

        repos = load_json_objects(f"{data_dir}/raw_repos_info/raw_repos_info.json")
        all_repos += repos
        print(f"There are {len(repos)} repos.")

        counts = count_owners(repos)

        log_dir = "log_file/get_data"

        # print("👤 Owner:")
        with open(f"{log_dir}/owner_{language}.log", "w", encoding="utf-8") as f:
            for owner, count in counts.most_common():
                line = f"{owner}: {count}\n"
                # print(line.strip())
                f.write(line)

        counts = count_languages(repos)
        # print("\n💻 Language:")
        with open(f"{log_dir}/language_{language}.log", "w", encoding="utf-8") as f:
            for language, count in counts.most_common():
                line = f"{language}: {count}\n"
                # print(line.strip())
                f.write(line)

    os.makedirs('data/raw_repos_info', exist_ok=True)
    with open(f'data/raw_repos_info/raw_repos_info.json', "w", encoding="utf-8", newline='\n') as f:
        json.dump(all_repos, f, indent=2)
    with open(f'data/raw_repos_info/raw_repos_info.jsonl', "w", encoding="utf-8") as f:
        for item in all_repos:
            f.write(json.dumps(item) + "\n")