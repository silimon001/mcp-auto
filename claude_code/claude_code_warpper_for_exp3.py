import subprocess
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from dataset_setting import dataset_name, framework_name

LOG_DIR = Path(os.getcwd()) / "log_file" / dataset_name / (framework_name + '_3') / 'qwen3.5-plus'
LOG_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def run_claude_stream(prompt_text: str, json_log_path: str):
    """
    流式运行 Claude，并实时写 JSONL

    修复内容：
    1. 收到 result 后立即终止 Claude 进程
    2. 避免 readline 永久阻塞
    3. 后台线程持续消费 stderr，防止 pipe deadlock
    4. 增加超时保护
    5. 更稳健的异常处理
    """

    import threading
    import queue

    process = subprocess.Popen(
        [
            "claude-tap",
            "--tap-live",
            "--",
            "--print",
            "--verbose",
            "--max-turns", "20",
            "--output-format", "stream-json",
            "--permission-mode", "bypassPermissions"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1
    )

    # =========================
    # 输入 prompt
    # =========================
    process.stdin.write(prompt_text)
    process.stdin.close()

    events = []
    stderr_lines = []

    # 用 queue 做线程安全通信
    stdout_queue = queue.Queue()
    stderr_queue = queue.Queue()

    # =========================
    # 后台消费 stdout
    # =========================
    def read_stdout():
        try:
            for line in iter(process.stdout.readline, ''):
                stdout_queue.put(line)
        except Exception as e:
            stdout_queue.put(f"__ERROR__:{e}")
        finally:
            stdout_queue.put(None)

    # =========================
    # 后台消费 stderr
    # =========================
    def read_stderr():
        try:
            for line in iter(process.stderr.readline, ''):
                stderr_queue.put(line)
                stderr_lines.append(line)
        except Exception as e:
            stderr_queue.put(f"__ERROR__:{e}")
        finally:
            stderr_queue.put(None)

    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)

    stdout_thread.start()
    stderr_thread.start()

    got_result = False

    # =========================
    # 主事件循环
    # =========================
    with open(json_log_path, "a", encoding="utf-8") as jf:

        while True:

            try:
                line = stdout_queue.get(timeout=1)

            except queue.Empty:

                # 已收到 result，则不再继续等待
                if got_result:
                    break

                # 子进程退出
                if process.poll() is not None:
                    break

                continue

            # stdout EOF
            if line is None:
                break

            line = line.strip()

            if not line:
                continue

            try:
                obj = json.loads(line)

                obj["_received_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                events.append(obj)

                jf.write(
                    json.dumps(
                        obj,
                        ensure_ascii=False
                    ) + "\n"
                )

                # 减少 flush 开销
                jf.flush()

                # =========================
                # 收到最终 result
                # =========================
                if obj.get("type") == "result":

                    got_result = True

                    # 非常关键：
                    # 不再等待 Claude 主进程自然退出
                    try:
                        process.terminate()
                    except Exception:
                        pass

                    break

            except json.JSONDecodeError:
                continue

            except Exception as e:
                print(f"⚠️ JSON parse error: {e}")

    # =========================
    # 等待退出
    # =========================
    try:
        process.wait(timeout=5)

    except subprocess.TimeoutExpired:

        print("⚠️ Claude process timeout, killing...")

        try:
            process.kill()
        except Exception:
            pass

    # =========================
    # 确保线程结束
    # =========================
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)

    stderr = "".join(stderr_lines)

    return events, stderr

def render_content(obj):
    """
    把 Claude stream-json content 递归展开成纯 string
    """
    if obj is None:
        return ""

    # str
    if isinstance(obj, str):
        return obj

    # dict（核心：Claude node）
    if isinstance(obj, dict):
        t = obj.get("type")

        # tool result wrapper
        if t == "text":
            return render_content(obj.get("text"))

        if t == "tool_result":
            return render_content(obj.get("content"))

        # fallback：尽量抽取 text
        if "text" in obj:
            return render_content(obj["text"])

        return json.dumps(obj, ensure_ascii=False)

    # list（递归 flatten）
    if isinstance(obj, list):
        return "\n".join(render_content(x) for x in obj)

    # fallback
    return str(obj)


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
            text = render_content(contents)
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
    with open(log_file, "a", encoding="utf-8") as f:
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

    json_log_path = f"{LOG_DIR}/tmp_{task_name}.jsonl"

    events, stderr = run_claude_stream(
        prompt_text,
        json_log_path
    )

    messages, order = collect_messages(events)
    log_file = f"{LOG_DIR}/{pos}_{pos+count}_{timestamp}.log"
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

    os.makedirs('mcp_server', exist_ok=True)
    os.makedirs('mcp_server_config', exist_ok=True)
    with open('mcp_server_config/config.json', 'w', encoding='utf-8') as f:
        f.write('{\n\n}')

    with open('claude_code/prompt_for_exp3.md', 'r', encoding='utf-8') as f:
        task_prompt = f.read()

    task_prompt = task_prompt.replace("{WORKSPACE}", os.getcwd())
    print(task_prompt)

    from glob import glob
    # 获取待处理的 README 文件列表
    readme_dir = Path.cwd() / "data" / "dataset" / dataset_name / "sampled_validated_readme"
    readme_files = sorted(glob(str(readme_dir / "*.md")), key=os.path.getsize)
    
    pos = 1
    count = 1

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