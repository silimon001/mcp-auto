import subprocess
import json
import os
from datetime import datetime
from pathlib import Path

dataset_name = 'MCP-Bench'

LOG_DIR = f"log_file/{dataset_name}"
os.makedirs(LOG_DIR, exist_ok=True)


def run_claude(prompt_text: str):
    process = subprocess.Popen(
        [
            "claude",
            "-p",
            "--verbose",
            "do it",
            "--max-turns", "20",
            "--output-format", "stream-json",
            "--permission-mode",
            "bypassPermissions"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = process.communicate(input=prompt_text)

    return stdout, stderr

def parse_all(stdout: str):
    events = []

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return events


def collect_messages(events):
    messages = {}
    order = []  # 保证顺序

    for event in events:
        etype = event.get("type")

        # -------- system --------
        if etype == "system":
            order.append({
                "role": "system",
                "content": f"[SYSTEM] {event.get('subtype', '')}"
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
                "role": "user",
                "content": text
            })
            continue

        # -------- assistant --------
        if etype == "assistant":
            msg = event.get("message", {})
            msg_id = msg.get("id")

            if msg_id not in messages:
                messages[msg_id] = {
                    "role": "assistant",
                    "texts": [],
                    "tools": [],
                    "tokens": None
                }
                order.append(msg_id)

            entry = messages[msg_id]

            # ---- content ----
            for c in msg.get("content", []):
                ctype = c.get("type")

                if ctype == "text":
                    entry["texts"].append(c.get("text", ""))

                elif ctype == "tool_use":
                    entry["tools"].append({
                        "name": c.get("name"),
                        "input": c.get("input")
                    })

            # ---- usage（只会在最终出现）----
            if msg.get("usage"):
                entry["tokens"] = {
                    "input": msg["usage"].get("input_tokens"),
                    "output": msg["usage"].get("output_tokens")
                }

    return messages, order

def write_log(messages, order, log_file):
    with open(log_file, "w", encoding="utf-8") as f:

        for item in order:

            # -------- system / user --------
            if isinstance(item, dict):
                f.write(f"\n[{item['role'].upper()}]:\n{item['content']}\n")
                f.write("\n" + "-" * 60 + "\n")
                continue

            # -------- assistant --------
            msg = messages[item]

            # 合并文本
            text = "\n".join(msg["texts"]).strip()

            if text:
                f.write(f"\n[ASSISTANT]:\n{text}\n")

            # tool
            for tool in msg["tools"]:
                f.write(f"\n[ASSISTANT][TOOL]: {tool['name']}\n")
                f.write("[TOOL INPUT]:\n")
                f.write(json.dumps(tool["input"], indent=2, ensure_ascii=False))
                f.write("\n")

            # tokens（只写一次）
            if msg["tokens"]:
                t = msg["tokens"]
                f.write(f"\n[TOKENS] input={t['input']} output={t['output']}\n")

            f.write("\n" + "-" * 60 + "\n")

def run_task(prompt_text: str, task_name="task"):
    stdout, stderr = run_claude(prompt_text)

    with open(f"{LOG_DIR}/json.log", 'w', encoding='utf-8') as f:
        f.write(stdout)

    events = parse_all(stdout)

    messages, order = collect_messages(events)

    log_file = f"{LOG_DIR}/{task_name}.log"
    write_log(messages, order, log_file)

    if stderr:
        with open(log_file, "a") as f:
            f.write("\n[STDERR]\n")
            f.write(stderr)

    print(f"✅ Done: {log_file}")


# =========================
# 6. 示例入口
# =========================
if __name__ == "__main__":
    # 假设你已经拼接好
    with open("/home/silimon/mcp-auto/mcp-auto/prompt/prompt_workflow.md", 'r', encoding='utf-8') as f:
        prompt_text = f.read()

    run_task(prompt_text, task_name="demo")