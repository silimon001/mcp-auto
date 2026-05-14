
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


# ============================================================
# 1. 正则
# ============================================================

# 一个任务结束标记
RESULT_RE = re.compile(
    r"=+\s*\n\[RESULT\].*?\n.*?状态:.*?$",
    re.MULTILINE | re.DOTALL
)

# TURN
TURN_RE = re.compile(
    r"\[TURN\s+(\d+)\]"
)

# tool 名
TOOL_RE = re.compile(
    r"\[ASSISTANT\]\[TOOL\]:\s*(.+)"
)

# TOOL INPUT
TOOL_INPUT_RE = re.compile(
    r"\[TOOL INPUT\]:\s*(.*?)"
    r"(?=\n\[|\Z)",
    re.DOTALL
)

# 状态
DONE_RE = re.compile(r"✅\s*@@Task Done@@")
FAILED_RE = re.compile(r"❌\s*@@Task Failed@@")


# ============================================================
# 2. 数据结构
# ============================================================

@dataclass
class SegmentRecord:
    serial_number: int
    status: str
    loops: List[LoopRecord] = field(default_factory=list)

@dataclass
class ToolCall:
    tool_name: str
    tool_args: str


@dataclass
class LoopRecord:
    loop_id: int
    tool_calls: list[ToolCall] = field(default_factory=list)


# ============================================================
# 3. Segment 切分
# ============================================================

def split_segments(text: str) -> list[str]:
    """
    用 [RESULT] 分割多个任务段。
    """

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

    # 最后残留
    tail = text[start:].strip()

    if tail:
        segments.append(tail)

    return segments


# ============================================================
# 4. 提取状态
# ============================================================

def extract_status(segment: str) -> str:
    """
    优先：
    DONE
    FAILED

    如果没有任何 flag：
    默认 FAILED
    """

    if DONE_RE.search(segment):
        return "✅ @@Task Done@@"

    if FAILED_RE.search(segment):
        return "❌ @@Task Failed@@"

    return "❌ @@Task Failed@@"


# ============================================================
# 5. 提取 loops
# ============================================================

import json
import re
from collections import OrderedDict


TURN_RE = re.compile(r"\[TURN\s+(\d+)\]")
TOOL_RE = re.compile(r"\[ASSISTANT\]\[TOOL\]:\s*(.+)")


def compact_json(raw: str) -> str:

    raw = raw.strip()

    if not raw:
        return "{}"

    try:

        data = json.loads(raw)

        if isinstance(data, dict):
            data.pop("description", None)

        return json.dumps(
            data,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    except Exception:

        # fallback:
        return " ".join(
            raw.split()
        )

def parse_loops(segment: str) -> list[LoopRecord]:
    lines = segment.splitlines()
    loop_map: OrderedDict[int, LoopRecord] = OrderedDict()
    current_turn = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # -------------------------------------------------
        # TURN
        # -------------------------------------------------
        m = TURN_RE.search(line)
        if m:
            turn_id = int(m.group(1))
            # 跳过 turn 0（初始化）
            if turn_id == 0:
                current_turn = None
                i += 1
                continue

            current_turn = turn_id
            if current_turn not in loop_map:
                loop_map[current_turn] = LoopRecord(loop_id=current_turn)
            i += 1
            continue

        # -------------------------------------------------
        # TOOL
        # -------------------------------------------------
        m = TOOL_RE.search(line)
        if m and current_turn is not None:
            tool_name = m.group(1).strip()
            i += 1
            while i < len(lines):
                if "[TOOL INPUT]:" in lines[i]:
                    break
                if TOOL_RE.search(lines[i]):
                    break
                if TURN_RE.search(lines[i]):
                    break
                i += 1

            raw_args = "{}"
            if i < len(lines) and "[TOOL INPUT]:" in lines[i]:
                i += 1
                arg_lines = []
                while i < len(lines):
                    nxt = lines[i]
                    if TURN_RE.search(nxt):
                        break
                    if TOOL_RE.search(nxt):
                        break
                    if nxt.startswith("[TOKENS]"):
                        break
                    if nxt.startswith("------------------------------------------------------------"):
                        break
                    arg_lines.append(nxt)
                    i += 1
                raw_args = "\n".join(arg_lines)

            cleaned_args = compact_json(raw_args)
            loop_map[current_turn].tool_calls.append(
                ToolCall(tool_name=tool_name, tool_args=cleaned_args)
            )
            continue

        i += 1

    # 重新编号，从 1 开始连续
    final_loops = []
    for new_idx, (_, loop) in enumerate(loop_map.items(), start=1):
        loop.loop_id = new_idx
        final_loops.append(loop)

    return final_loops


# ============================================================
# 6. 解析整个日志
# ============================================================

def simplify_log_text(text: str) -> list[SegmentRecord]:

    segments = split_segments(text)

    results: list[SegmentRecord] = []

    for idx, seg in enumerate(segments, start=1):

        status = extract_status(seg)

        loops = parse_loops(seg)

        results.append(
            SegmentRecord(
                serial_number=idx,
                status=status,
                loops=loops,
            )
        )

    return results


# ============================================================
# 7. 输出简化日志
# ============================================================

def write_simplified_log(
    records: list[SegmentRecord],
    output_path: Path,
):

    lines: list[str] = []

    for seg in records:

        lines.append(
            f"{seg.serial_number} | {seg.status}"
        )

        for loop in seg.loops:

            # 没有 tool call
            if not loop.tool_calls:

                lines.append(
                    f"loop {loop.loop_id} | 无 tool_calls"
                )

                continue

            tool_parts = []

            for tc in loop.tool_calls:

                tool_parts.append(
                    f"Tool={tc.tool_name}, Args={tc.tool_args}"
                )

            merged = " ; ".join(tool_parts)

            lines.append(
                f"loop {loop.loop_id} | {merged}"
            )

        lines.append("")

    output_path.write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8"
    )


# ============================================================
# 8. 主入口
# ============================================================

def simplify_logs(log_paths: list[str]) -> list[Path]:

    outputs = []

    for path_str in log_paths:

        path = Path(path_str)

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        records = simplify_log_text(text)

        output_path = path.with_name(
            f"s_{path.stem}.log"
        )

        write_simplified_log(records, output_path)

        outputs.append(output_path)

    return outputs


# ============================================================
# 9. CLI
# ============================================================

if __name__ == "__main__":

    from dataset_setting import dataset_name, framework_name

    log_sources: list[str] = [
        f"log_file/{dataset_name}/{framework_name}/qwen3.5-plus/" + x
        for x in [
            '0_40_2026-05-14_18-22-39.log',
            '40_80_2026-05-14_20-07-47.log',
            '80_120_2026-05-14_21-45-25.log',
            '120_160_2026-05-14_23-11-23.log'
        ]
    ]

    outputs = simplify_logs(log_sources)

    for p in outputs:
        print("written:", p)