import subprocess, json, os, re, sys, threading, queue
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List
from exp_setting import dataset_name, framework_name, model_name
from glob import glob

HOME, CWD = Path.home(), Path.cwd()
LOG_DIR = CWD / "log_file" / dataset_name / framework_name / model_name
LOG_DIR.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def run_claude_stream(prompt_text: str):
    process = subprocess.Popen(
        ["claude-tap", "--", "--print", "--verbose", "--max-turns", "20",
         "--output-format", "stream-json", "--permission-mode", "bypassPermissions",
         "--exclude-dynamic-system-prompt-sections"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", bufsize=1
    )
    process.stdin.write(prompt_text)
    process.stdin.close()

    events, stderr_lines = [], []
    stdout_queue, stderr_queue = queue.Queue(), queue.Queue()

    def read_stdout():
        try:
            for line in iter(process.stdout.readline, ''):
                stdout_queue.put(line)
        except Exception as e:
            stdout_queue.put(f"__ERROR__:{e}")
        finally:
            stdout_queue.put(None)

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

    while True:
        try:
            line = stdout_queue.get(timeout=1)
        except queue.Empty:
            if got_result or process.poll() is not None:
                break
            continue

        if line is None:
            break

        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
            obj["_received_at"] = datetime.now(timezone.utc).isoformat()
            events.append(obj)

            if obj.get("type") == "result":
                got_result = True
                try:
                    process.terminate()
                except Exception:
                    pass
                break

        except json.JSONDecodeError:
            continue
        except Exception as e:
            print(f"⚠️ JSON parse error: {e}")

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("⚠️ Claude process timeout, killing...")
        try:
            process.kill()
        except Exception:
            pass

    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)

    return events, "".join(stderr_lines)

@dataclass
class NormalizedEvent:
    turn: int
    event_type: str
    timestamp: str
    payload: dict
    raw: dict

class ClaudeStreamParser:
    def __init__(self): self.tool_calls = {}; self.turn = 0

    def parse_events(self, events: List[Dict[str, Any]]) -> List[NormalizedEvent]:
        result = []
        for obj in events:
            parsed = self.parse_event(obj)
            if not parsed: continue
            if isinstance(parsed, list): result.extend(parsed)
            else: result.append(parsed)
        return result

    def parse_event(self, obj: Dict[str, Any]):
        typ = obj.get("type")
        if typ == "system": return self._parse_system(obj)
        elif typ == "assistant": return self._parse_assistant(obj)
        elif typ == "user": return self._parse_user(obj)
        elif typ == "result": return self._parse_result(obj)
        return None

    def _parse_system(self, obj):
        subtype, ts = obj.get("subtype"), obj.get("_received_at")
        if subtype == "init":
            return NormalizedEvent(0, "SESSION_INIT", ts, {}, obj)
        return None

    def _parse_assistant(self, obj):
        ts = obj.get("_received_at")
        content = obj.get("message", {}).get("content", [])
        events = []
        for block in content:
            btype = block.get("type")
            if btype == "thinking":
                self.turn += 1
                events.append(NormalizedEvent(self.turn, "ASSISTANT_THINKING", ts, {"thinking": block.get("thinking", "")}, obj))
            elif btype == "text":
                events.append(NormalizedEvent(self.turn, "ASSISTANT_TEXT", ts, {"text": block.get("text", "")}, obj))
            elif btype == "tool_use":
                tool_id = block.get("id")
                self.tool_calls[tool_id] = {"tool": block.get("name"), "input": block.get("input"), "start_time": ts, "result": None}
                events.append(NormalizedEvent(self.turn, "TOOL_CALL", ts, {"tool_use_id": tool_id, "tool_name": block.get("name"), "input": block.get("input")}, obj))
        return events

    def _parse_user(self, obj):
        ts = obj.get("_received_at"); events = []
        for block in obj.get("message", {}).get("content", []):
            tool_use_id = block.get("tool_use_id")
            if not tool_use_id: continue
            result_data = block.get("content"); duration = None
            if tool_use_id in self.tool_calls:
                call = self.tool_calls[tool_use_id]
                call["result"] = result_data; call["end_time"] = ts
                try: duration = (datetime.fromisoformat(ts) - datetime.fromisoformat(call["start_time"])).total_seconds()
                except Exception: pass
            events.append(NormalizedEvent(self.turn, "TOOL_RESULT", ts,
                {"tool_use_id": tool_use_id, "result": result_data, "is_error": block.get("is_error", False), "duration_seconds": duration}, obj))
        return events

    def _parse_result(self, obj):
        return NormalizedEvent(self.turn, "FINAL_RESULT", obj.get("_received_at"),
            {"subtype": obj.get("subtype"), "duration_ms": obj.get("duration_ms"),
             "duration_api_ms": obj.get("duration_api_ms"), "num_turns": obj.get("num_turns"),
             "result": obj.get("result"), "total_cost_usd": obj.get("total_cost_usd"),
             "usage": obj.get("usage"), "is_error": obj.get("is_error")}, obj)

    def get_tool_summary(self):
        summary = []
        for tool_id, info in self.tool_calls.items():
            duration = None
            if "start_time" in info and "end_time" in info:
                try: duration = (datetime.fromisoformat(info["end_time"]) - datetime.fromisoformat(info["start_time"])).total_seconds()
                except Exception: pass
            summary.append({"tool_use_id": tool_id, "tool": info["tool"], "duration_seconds": duration, "success": info.get("result") is not None})
        return summary

    @staticmethod
    def to_json(events): return [asdict(e) for e in events]

def write_timeline_log(timeline, log_file):
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        for event in timeline:
            if event.event_type == "SESSION_INIT":
                f.write(f"[{event.timestamp}] {event.event_type}\n")
            elif event.event_type == "FINAL_RESULT":
                f.write(f"status={event.payload.get('subtype')}\n")
                f.write(f"turns={event.payload.get('num_turns')}\n")
                f.write(f"duration_ms={event.payload.get('duration_ms')}\n")
                f.write(f"api_ms={event.payload.get('duration_api_ms')}\n")
                f.write(f"cost_usd={event.payload.get('total_cost_usd')}\n")
                usage = event.payload.get("usage")
                if usage:
                    f.write("\nTOKEN USAGE:\n")
                    for k, v in usage.items(): f.write(f"  {k}: {v}\n")
                f.write("\n")
            else:
                etype, payload = event.event_type, event.payload
                f.write(f"[Turn {event.turn}] [{event.timestamp}] {etype}\n")
                if etype == "ASSISTANT_TEXT": f.write(payload.get("text", "") + '\n')
                elif etype == "ASSISTANT_THINKING": f.write(payload.get("thinking", "") + "\n")
                elif etype == "TOOL_CALL":
                    f.write(f"tool={payload.get('tool_name')}, ")
                    f.write(f"args={json.dumps(payload.get('input', {}), ensure_ascii=False)}\n")
                elif etype == "TOOL_RESULT":
                    if payload.get("duration_seconds") is not None: f.write(f"duration={payload['duration_seconds']:.2f}s\n")
                    if payload.get("is_error"): f.write("ERROR=True\n")
                    result = payload.get("result")
                    if result: f.write("\nOUTPUT\n" + str(result) + "\n")
            f.write("-" * 80 + "\n")

def run_task(prompt_text: str, task_name, pos, count):
    events, stderr = run_claude_stream(prompt_text)
    parser = ClaudeStreamParser()
    timeline = parser.parse_events(events)
    log_file = f"{LOG_DIR}/{pos}_{pos+count}_{timestamp}.log"
    write_timeline_log(timeline, log_file)
    return timeline

def add_extra_info(dataset_name: str, repo_id: str) -> str:
    final_text = ''
    repo_info_path = CWD / "data" / "dataset" / dataset_name / "repo_info.json"
    if repo_info_path.exists():
        with open(repo_info_path, 'r', encoding='utf-8') as f: repo_infos = json.load(f)
        for repo_info in repo_infos:
            if repo_info.get('id') == int(repo_id):
                info = {k: repo_info.get(k) for k in ["id", "description", "language", "size", "topic", "html_url"]}
                info['owner'] = repo_info.get('full_name').split('/')[0]
                info['name'] = repo_info.get('full_name').split('/')[1]
                final_text += f'\n=== REPO INFO START ===\n{info}\n=== REPO INFO END ===\n'
                break
    return final_text

def verify_model(model_name: str):
    settings_path = HOME / ".claude" / "settings.json"
    if not settings_path.exists(): print("settings.json not found"); sys.exit(1)
    settings = json.loads(settings_path.read_text())
    anthropic_model = settings.get('env', {}).get("ANTHROPIC_MODEL")
    if not anthropic_model: print("ANTHROPIC_MODEL not found in settings.json"); sys.exit(1)
    if anthropic_model != model_name: print(f"Model mismatch:\nexpected: {model_name}\nactual:   {anthropic_model}"); sys.exit(1)
    print(f"Model verified: {anthropic_model}")


def env_ready():
    import shutil
    mcp_file = CWD / ".mcp.json"
    if mcp_file.exists(): mcp_file.unlink(); print("Deleted .mcp.json")
    skills_dir = CWD / ".claude"
    if skills_dir.exists(): shutil.rmtree(skills_dir); print(f"Deleted {skills_dir} folder")
    claude_md = CWD / 'CLAUDE.md'
    if claude_md.exists(): claude_md.unlink(); print(f"Deleted {claude_md}")
    print('ENV init done')

if __name__ == "__main__":
    os.makedirs('mcp_server', exist_ok=True); os.makedirs('mcp_server_config', exist_ok=True)
    with open('mcp_server_config/config.json', 'w', encoding='utf-8') as f: f.write('{\n  "mcpServers": {\n\n  }\n}')
    with open('claude_code/prompt_for_exp1.md', 'r', encoding='utf-8') as f: task_prompt = f.read()
    task_prompt = task_prompt.replace("{WORKSPACE}", str(CWD))
    readme_dir = CWD / "data" / "dataset" / dataset_name / "sampled_validated_readme"
    readme_files = sorted(glob(str(readme_dir / "*.md")), key=os.path.getsize)
    pos, count = 0, 40
    for readme_path in readme_files[pos:pos+count]:
        verify_model(model_name); env_ready()
        readme_path = Path(readme_path); filename_parts = readme_path.stem.split('_'); repo_id = filename_parts[0]
        with open(readme_path, 'r', encoding='utf-8') as f: readme_content = f.read()
        extra_info = add_extra_info(dataset_name, repo_id)
        query = f'\n=== README.md START ===\n{readme_content}\n=== README.md END ===\n{extra_info}'
        all_prompt = task_prompt + query
        run_task(all_prompt, "claude_code", pos, count)