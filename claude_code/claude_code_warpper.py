import subprocess
import json
import os
from datetime import datetime
from pathlib import Path
from dataset_setting import dataset_name

LOG_DIR = f"log_file/{dataset_name}"
os.makedirs(LOG_DIR, exist_ok=True)


def run_claude(prompt_text: str):
    process = subprocess.Popen(
        [
            "claude",
            "--print",
            "--verbose",
            "--max-turns", "20",
            "--output-format", "stream-json",
            "--permission-mode", "bypassPermissions"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = process.communicate(input=prompt_text)

    return stdout, stderr

from datetime import datetime, timezone

def parse_all(stdout: str):
    """解析 stream-json 行，并为每条事件记录接收时间"""
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            # 添加我们接收到这一行的时间戳（UTC）
            event["_received_at"] = datetime.now(timezone.utc).isoformat()
            events.append(event)
        except json.JSONDecodeError:
            continue
    return events


def collect_messages(events):
    """聚合事件，记录时间戳，并捕获 result 事件用于总结"""
    messages = {}
    order = []      # dict(system/user/result) 或 str(assistant msg_id)

    for event in events:
        etype = event.get("type")
        ts = event.get("timestamp") or event.get("_received_at", datetime.now(timezone.utc).isoformat())

        # -------- system --------
        if etype == "system":
            order.append({
                "type": "system",
                "content": f"[SYSTEM] {event.get('subtype', '')}",
                "timestamp": ts
            })
            continue

        # -------- user --------
        if etype == "user":
            contents = event.get("message", {}).get("content", [])
            text = "\n".join(
                c.get("content", "") if c.get("type") == "tool_result"
                else c.get("text", "")
                for c in contents
            )
            order.append({
                "type": "user",
                "content": text,
                "timestamp": ts
            })
            continue

        # -------- result (最终总结) --------
        if etype == "result":
            order.append({
                "type": "result",
                "timestamp": ts,
                "data": {
                    "subtype": event.get("subtype"),
                    "is_error": event.get("is_error"),
                    "num_turns": event.get("num_turns"),
                    "stop_reason": event.get("stop_reason"),
                    "total_cost_usd": event.get("total_cost_usd"),
                    "duration_ms": event.get("duration_ms"),
                    "duration_api_ms": event.get("duration_api_ms"),
                    "usage": event.get("usage", {}),
                    "errors": event.get("errors", []),
                    "terminal_reason": event.get("terminal_reason")
                }
            })
            continue

        # -------- assistant --------
        if etype == "assistant":
            msg = event.get("message", {})
            msg_id = msg.get("id")

            if msg_id not in messages:
                messages[msg_id] = {
                    "type": "assistant",
                    "texts": [],
                    "tools": [],
                    "tokens": None,
                    "timestamp": ts
                }
                order.append(msg_id)     # 保证顺序

            entry = messages[msg_id]

            for c in msg.get("content", []):
                ctype = c.get("type")
                if ctype == "text":
                    entry["texts"].append(c.get("text", ""))
                elif ctype == "tool_use":
                    entry["tools"].append({
                        "name": c.get("name"),
                        "input": c.get("input")
                    })

            if msg.get("usage"):
                entry["tokens"] = {
                    "input": msg["usage"].get("input_tokens"),
                    "output": msg["usage"].get("output_tokens")
                }

    return messages, order


def write_log(messages, order, log_file):
    """按轮次和时间戳输出，末尾附加任务结果总结"""
    turn = 0
    with open(log_file, "w", encoding="utf-8") as f:
        for item in order:
            # -------- 结果总结（直接输出，不改变轮次）--------
            if isinstance(item, dict) and item.get("type") == "result":
                ts = item.get("timestamp", "")
                data = item["data"]

                f.write(f"\n{'=' * 60}\n")
                f.write(f"[RESULT] [TIMESTAMP {ts}]\n")
                f.write(f"  状态: {'❌ 失败' if data['is_error'] else '✅ 成功'}\n")
                f.write(f"  子类型: {data['subtype']}\n")
                f.write(f"  实际轮次: {data['num_turns']}\n")
                f.write(f"  停止原因: {data['stop_reason']}\n")
                f.write(f"  终端原因: {data['terminal_reason']}\n")
                f.write(f"  耗时: {data['duration_ms']} ms (API: {data['duration_api_ms']} ms)\n")
                f.write(f"  成本: ${data['total_cost_usd']:.6f}\n")

                usage = data.get("usage", {})
                if usage:
                    f.write(f"  Token 使用:\n")
                    f.write(f"    - 输入: {usage.get('input_tokens', '?')}\n")
                    f.write(f"    - 输出: {usage.get('output_tokens', '?')}\n")
                    f.write(f"    - 缓存创建: {usage.get('cache_creation_input_tokens', '?')}\n")
                    f.write(f"    - 缓存读取: {usage.get('cache_read_input_tokens', '?')}\n")

                errors = data.get("errors", [])
                if errors:
                    f.write(f"  错误信息:\n")
                    for err in errors:
                        f.write(f"    - {err}\n")
                f.write(f"{'=' * 60}\n")
                continue   # result 块输出完毕，跳过后续普通处理

            # -------- system / user --------
            if isinstance(item, dict):
                role = item["type"].upper()
                ts = item.get("timestamp", "")
                f.write(f"\n[TURN {turn}] [TIMESTAMP {ts}]\n")
                f.write(f"[{role}]:\n{item['content']}\n")
                f.write("\n" + "-" * 60 + "\n")
                continue

            # -------- assistant --------
            turn += 1
            msg = messages[item]
            ts = msg.get("timestamp", "")
            f.write(f"\n[TURN {turn}] [TIMESTAMP {ts}]\n")

            text = "\n".join(msg["texts"]).strip()
            if text:
                f.write(f"[ASSISTANT]:\n{text}\n")

            for tool in msg["tools"]:
                f.write(f"[ASSISTANT][TOOL]: {tool['name']}\n")
                f.write("[TOOL INPUT]:\n")
                f.write(json.dumps(tool["input"], indent=2, ensure_ascii=False))
                f.write("\n")

            if msg["tokens"]:
                t = msg["tokens"]
                f.write(f"[TOKENS] input={t['input']} output={t['output']}\n")

            f.write("\n" + "-" * 60 + "\n")

def run_task(prompt_text: str, task_name, pos, count):
    stdout, stderr = run_claude(prompt_text)

    # 解析 stdout (JSONL 格式) 为 Python 对象列表
    log_entries = []
    for line in stdout.strip().splitlines():
        line = line.strip()
        if line:  # 跳过空行
            try:
                log_entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                # 可选：记录解析失败的行
                print(f"警告：跳过无效 JSON 行 - {e}")

    # 写入缩进排列的 JSON 文件
    with open(f"{LOG_DIR}/{task_name}.json", "w", encoding="utf-8") as f:
        json.dump(log_entries, f, indent=2, ensure_ascii=False)


    events = parse_all(stdout)

    messages, order = collect_messages(events)

    log_file = f"{LOG_DIR}/EXP_{dataset_name}_{pos+count}_{task_name}.log"
    write_log(messages, order, log_file)

    if stderr:
        with open(log_file, "a") as f:
            f.write("\n[STDERR]\n")
            f.write(stderr)

    print(f"✅ Done: {log_file}")


# ==================== 工具函数 ====================
def add_extra_info(dataset_name: str, repo_id: str) -> str:
    """从数据集读取仓库额外信息"""
    final_text = ''
    repo_info_path = Path.cwd() / "data" / "dataset" / dataset_name / "repo_info.json"
    if repo_info_path.exists():
        with open(repo_info_path, 'r', encoding='utf-8') as f:
            repo_infos = json.load(f)
        for repo_info in repo_infos:
            if repo_info.get('id') == int(repo_id):
                info = {k: repo_info.get(k) for k in ["id", "description", "language", "size", "topic", "html_url"]}
                info['owner'] = repo_info.get('full_name').split('/')[0]
                info['name'] = repo_info.get('full_name').split('/')[1]
                final_text += f'\n=== REPO INFO START ===\n{info}\n=== REPO INFO END ===\n'
                break
    return final_text


# =========================
# 6. 示例入口
# =========================
if __name__ == "__main__":
    
    with open('claude_code/prompt_workflow.md', 'r', encoding='utf-8') as f:
        task_prompt = f.read()

    task_prompt = task_prompt.replace("{WORKSPACE}", os.getcwd())
    print(task_prompt)

    from glob import glob
    # 获取待处理的 README 文件列表
    readme_dir = Path.cwd() / "data" / "dataset" / dataset_name / "sampled_validated_readme"
    readme_files = sorted(glob(str(readme_dir / "*.md")), key=os.path.getsize)
    
    pos = 0
    count = 30

    for readme_path in readme_files[pos:pos+count]:
        readme_path = Path(readme_path)
        filename_parts = readme_path.stem.split('_')
        repo_id = filename_parts[0]
        repo_name = '_'.join(filename_parts[1:]).replace('_README', '')

        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        extra_info = add_extra_info(dataset_name, repo_id)

        query = f'''\n=== README.md START ===\n{readme_content}\n=== README.md END ===\n{extra_info}'''

        all_prompt = task_prompt + query

        print(all_prompt)

        run_task(all_prompt, "claude_code", pos, count)