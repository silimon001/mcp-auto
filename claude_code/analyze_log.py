from __future__ import annotations

import json
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional


# ========================== 正则定义 ==========================
RESULT_RE = re.compile(r"=+\s*\n\[RESULT\].*?(?=\n=+|\Z)", re.MULTILINE | re.DOTALL)
TURN_RE = re.compile(r"\[TURN\s+(\d+)\]")
TOOL_RE = re.compile(r"\[ASSISTANT\]\[TOOL\]:\s*(.+)")
SERVER_OK_RE = re.compile(r"^\[OK\]\s+The server\s+.+?\s+started successfully,\s+tools:\s+.+$", re.MULTILINE)
DONE_LINE_RE = re.compile(
    r"^\s*✅ @@Task Done@@\s*$",
    re.MULTILINE
)
TOKEN_USAGE_RE = re.compile(
    r"Token\s+使用:\s*\n\s*-\s+输入:\s*(\d+)\s*\n\s*-\s+输出:\s*(\d+)\s*\n\s*-\s+缓存创建:\s*(\d+)\s*\n\s*-\s+缓存读取:\s*(\d+)",
    re.MULTILINE
)


# ========================== 数据结构 ==========================
@dataclass
class ToolCall:
    tool_name: str
    tool_args: str

@dataclass
class LoopRecord:
    loop_id: int
    tool_calls: List[ToolCall] = field(default_factory=list)

@dataclass
class SegmentRecord:
    serial_number: int
    status: str                # "✅ @@Task Done@@" 或 "❌ @@Task Failed@@"
    loops: List[LoopRecord] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)


# ========================== 辅助函数 ==========================
def compact_json(raw: str) -> str:
    """将工具参数压缩为单行 JSON（移除 description 字段）"""
    raw = raw.strip()
    if not raw:
        return "{}"
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data.pop("description", None)
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return " ".join(raw.split())

def extract_token_usage(segment: str) -> Dict[str, int]:
    """从 [RESULT] 块中提取 token 用量"""
    result_match = RESULT_RE.search(segment)
    if not result_match:
        return {}
    m = TOKEN_USAGE_RE.search(result_match.group(0))
    if not m:
        return {}
    return {
        "input": int(m.group(1)),
        "output": int(m.group(2)),
        "cache_creation": int(m.group(3)),
        "cache_read": int(m.group(4))
    }

def extract_status(segment: str) -> str:
    """
    成功条件：同时存在 SERVER_OK_RE 和 DONE_LINE_RE
    注意：DONE_LINE_RE 可出现在任何位置（不一定在最后一轮）
    """
    has_server_ok = bool(SERVER_OK_RE.search(segment))
    has_done_flag = bool(DONE_LINE_RE.search(segment))
    if has_server_ok and has_done_flag:
        return "✅ @@Task Done@@"
    return "❌ @@Task Failed@@"

def split_segments(text: str) -> List[str]:
    """基于 [RESULT] 切分任务段"""
    matches = list(RESULT_RE.finditer(text))
    if not matches:
        return [text]
    segments = []
    start = 0
    for m in matches:
        end = m.end()
        seg = text[start:end].strip()
        if seg:
            segments.append(seg)
        start = end

    return segments

def parse_loops(segment: str) -> List[LoopRecord]:
    """提取所有工具调用，按 TURN 分组，并重新编号"""
    lines = segment.splitlines()
    loop_map = OrderedDict()          # turn_id -> LoopRecord
    current_turn = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # 匹配 [TURN X]
        m = TURN_RE.search(line)
        if m:
            turn_id = int(m.group(1))
            if turn_id == 0:
                current_turn = None
                i += 1
                continue
            current_turn = turn_id
            if current_turn not in loop_map:
                loop_map[current_turn] = LoopRecord(loop_id=current_turn)
            i += 1
            continue

        # 匹配 [ASSISTANT][TOOL]: tool_name
        m = TOOL_RE.search(line)
        if m and current_turn is not None:
            tool_name = m.group(1).strip()
            i += 1
            # 定位 [TOOL INPUT]:
            while i < len(lines):
                if "[TOOL INPUT]:" in lines[i]:
                    break
                if TOOL_RE.search(lines[i]) or TURN_RE.search(lines[i]):
                    break
                i += 1

            raw_args = "{}"
            if i < len(lines) and "[TOOL INPUT]:" in lines[i]:
                i += 1
                arg_lines = []
                while i < len(lines):
                    nxt = lines[i]
                    if TURN_RE.search(nxt) or TOOL_RE.search(nxt):
                        break
                    if nxt.startswith("[TOKENS]") or nxt.startswith("-" * 60):
                        break
                    arg_lines.append(nxt)
                    i += 1
                raw_args = "\n".join(arg_lines)

            cleaned_args = compact_json(raw_args)
            loop_map[current_turn].tool_calls.append(ToolCall(tool_name, cleaned_args))
            continue

        i += 1

    # 重新编号 loop (1,2,3...)
    final_loops = []
    for new_idx, (_, loop) in enumerate(loop_map.items(), start=1):
        loop.loop_id = new_idx
        final_loops.append(loop)
    return final_loops


# ========================== 主处理流程 ==========================
def simplify_log_text(text: str) -> List[SegmentRecord]:
    segments = split_segments(text)
    results = []
    for idx, seg in enumerate(segments, start=1):
        status = extract_status(seg)
        loops = parse_loops(seg)
        token_usage = extract_token_usage(seg)
        results.append(SegmentRecord(idx, status, loops, token_usage))
    return results

def write_simplified_log(records: List[SegmentRecord], output_path: Path) -> None:
    lines = []
    for seg in records:
        # 第一行：序号 | 状态 | token 用量（如果有）
        line = f"{seg.serial_number} | {seg.status}"
        if seg.token_usage:
            tu = seg.token_usage
            line += f" | Input: {tu['input']} Output: {tu['output']} cache_creation: {tu['cache_creation']} cache_read: {tu['cache_read']}"
        lines.append(line)

        # 工具调用记录
        for loop in seg.loops:
            if not loop.tool_calls:
                lines.append(f"loop {loop.loop_id} | 无 tool_calls")
            else:
                tool_strs = [f"Tool={tc.tool_name}, Args={tc.tool_args}" for tc in loop.tool_calls]
                lines.append(f"loop {loop.loop_id} | {' ; '.join(tool_strs)}")
        lines.append("")   # 空行分隔不同 segment

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

def simplify_logs(log_paths: List[str]) -> List[Path]:
    outputs = []
    for path_str in log_paths:
        path = Path(path_str)
        text = path.read_text(encoding="utf-8", errors="replace")
        records = simplify_log_text(text)
        out_path = path.with_name(f"s_{path.stem}.log")
        write_simplified_log(records, out_path)
        outputs.append(out_path)
    return outputs


# ========================== CLI 示例（可替换为自己的调用） ==========================
if __name__ == "__main__":
    # 这里只是一个示例，实际使用时请按需修改
    from dataset_setting import dataset_name, framework_name, model_name
    HOME = Path.home()
    log_sources = [
        str(HOME) + f"/mcp-auto/log_file/{dataset_name}/{framework_name + '_3'}/{model_name}/" + x
        for x in [
           '0_40_2026-05-20_23-56-06.log',
'0_40_2026-05-28_14-49-22.log',
'0_40_2026-05-28_16-52-15.log',
'40_80_2026-05-21_13-17-58.log',
'40_80_2026-05-28_18-29-20.log',
'40_80_2026-05-28_20-18-08.log',
'80_120_2026-05-21_14-24-28.log',
'80_120_2026-05-28_22-27-32.log',
'80_120_2026-05-29_09-10-32.log',
'120_160_2026-05-21_16-10-28.log',
'120_160_2026-05-29_11-42-57.log',
'120_160_2026-05-29_14-58-19.log',
'160_200_2026-05-21_18-10-38.log',
'160_200_2026-05-30_00-05-36.log',
'160_200_2026-05-30_21-43-07.log'
                  ]
    ]
    outputs = simplify_logs(log_sources)
    for p in outputs:
        print("written:", p)