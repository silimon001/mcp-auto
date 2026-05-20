from __future__ import annotations

import json
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


# ============================================================
# 1. 正则
# ============================================================

# RESULT block
RESULT_RE = re.compile(
    r"=+\s*\n\[RESULT\].*?(?=\n=+|\Z)",
    re.MULTILINE | re.DOTALL
)

# TURN
TURN_RE = re.compile(
    r"\[TURN\s+(\d+)\]"
)

# TOOL
TOOL_RE = re.compile(
    r"\[ASSISTANT\]\[TOOL\]:\s*(.+)"
)

# assistant 普通输出
ASSISTANT_RE = re.compile(
    r"\[ASSISTANT\](?!\[TOOL\])\s*:?(.*)",
)

# RESULT 状态
RESULT_FAIL_RE = re.compile(
    r"状态:\s*❌\s*失败"
)

RESULT_SUCCESS_RE = re.compile(
    r"状态:\s*✅\s*成功"
)

# DONE / FAILED FLAG
DONE_LINE_RE = re.compile(
    r"^\s*✅\s*@@Task Done@@\s*$"
)

FAILED_LINE_RE = re.compile(
    r"^\s*❌\s*@@Task Failed@@\s*$"
)

SERVER_OK_RE = re.compile(
    r"^\[OK\]\s+The server\s+.+?\s+started successfully,\s+tools:\s+.+$",
    re.MULTILINE
)

# ============================================================
# 2. 数据结构
# ============================================================

@dataclass
class ToolCall:
    tool_name: str
    tool_args: str


@dataclass
class LoopRecord:
    loop_id: int
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class SegmentRecord:
    serial_number: int
    status: str
    loops: List[LoopRecord] = field(default_factory=list)


# ============================================================
# 3. Segment 切分
# ============================================================

def split_segments(text: str) -> list[str]:
    """
    基于 [RESULT] 切分任务段
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

    tail = text[start:].strip()

    if tail:
        segments.append(tail)

    return segments


# ============================================================
# 4. assistant 输出提取
# ============================================================

def extract_last_assistant_message(segment: str) -> str:
    """
    仅提取最后一个 assistant 普通输出
    不包含:
        [ASSISTANT][TOOL]
    """

    lines = segment.splitlines()

    messages = []

    collecting = False
    current = []

    for line in lines:

        # TOOL 行直接结束
        if TOOL_RE.search(line):
            if collecting and current:
                messages.append("\n".join(current).strip())
            collecting = False
            current = []
            continue

        # assistant 开始
        if line.startswith("[ASSISTANT]") and "[TOOL]" not in line:

            if collecting and current:
                messages.append("\n".join(current).strip())

            collecting = True

            content = line.replace("[ASSISTANT]", "").strip(": ")

            current = [content]
            continue

        # 进入其它 block
        if line.startswith("[USER]") \
                or line.startswith("[SYSTEM]") \
                or line.startswith("[TOOL]") \
                or TURN_RE.search(line):

            if collecting and current:
                messages.append("\n".join(current).strip())

            collecting = False
            current = []
            continue

        # assistant continuation
        if collecting:
            current.append(line)

    if collecting and current:
        messages.append("\n".join(current).strip())

    if not messages:
        return ""

    return messages[-1]


# ============================================================
# 5. 提取状态（新逻辑）
# ============================================================

def extract_last_flag(message: str) -> str | None:
    """
    只识别：
        单独占一行的 flag

    返回：
        DONE
        FAILED
        None
    """

    flags = []

    for raw_line in message.splitlines():

        line = raw_line.strip()

        if DONE_LINE_RE.fullmatch(line):
            flags.append("DONE")

        elif FAILED_LINE_RE.fullmatch(line):
            flags.append("FAILED")

    if not flags:
        return None

    return flags[-1]

def extract_status(segment: str) -> str:
    """
    最终可靠判定逻辑：

    成功必须同时满足：

    1. segment 中存在:
       [OK] The server xxx started successfully

    2. 最后 assistant message 中
       最后一个独立行 flag 是:
       ✅ @@Task Done@@

    否则失败
    """

    # --------------------------------------------------------
    # 1. 必须存在 server started successfully
    # --------------------------------------------------------

    server_ok = bool(
        SERVER_OK_RE.search(segment)
    )

    if not server_ok:
        return "❌ @@Task Failed@@"

    # --------------------------------------------------------
    # 2. 提取最后 assistant message
    # --------------------------------------------------------

    last_msg = extract_last_assistant_message(segment)

    if not last_msg:
        return "❌ @@Task Failed@@"

    # --------------------------------------------------------
    # 3. 提取最后 flag
    # --------------------------------------------------------

    last_flag = extract_last_flag(last_msg)

    # --------------------------------------------------------
    # 4. 最终判定
    # --------------------------------------------------------

    if last_flag == "DONE":
        return "✅ @@Task Done@@"

    return "❌ @@Task Failed@@"

# ============================================================
# 6. compact json
# ============================================================

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

        return " ".join(
            raw.split()
        )


# ============================================================
# 7. 解析 loops
# ============================================================

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

            # 跳过 turn0
            if turn_id == 0:
                current_turn = None
                i += 1
                continue

            current_turn = turn_id

            if current_turn not in loop_map:
                loop_map[current_turn] = LoopRecord(
                    loop_id=current_turn
                )

            i += 1
            continue

        # -------------------------------------------------
        # TOOL
        # -------------------------------------------------

        m = TOOL_RE.search(line)

        if m and current_turn is not None:

            tool_name = m.group(1).strip()

            i += 1

            # 找 TOOL INPUT
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
                ToolCall(
                    tool_name=tool_name,
                    tool_args=cleaned_args,
                )
            )

            continue

        i += 1

    # turn 连续重编号
    final_loops = []

    for new_idx, (_, loop) in enumerate(
        loop_map.items(),
        start=1
    ):
        loop.loop_id = new_idx
        final_loops.append(loop)

    return final_loops


# ============================================================
# 8. 解析整个日志
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
# 9. 输出
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
        encoding="utf-8",
    )


# ============================================================
# 10. 主入口
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

        write_simplified_log(
            records,
            output_path,
        )

        outputs.append(output_path)

    return outputs


# ============================================================
# 11. CLI
# ============================================================

if __name__ == "__main__":

    from dataset_setting import (
        dataset_name,
        framework_name,
    )

    log_sources: list[str] = [
        f"log_file/{dataset_name}/{framework_name}/qwen3.5-plus/" + x
        for x in [
            '0_40_2026-05-13_16-11-13.log'
        ]
    ]

    outputs = simplify_logs(log_sources)

    for p in outputs:
        print("written:", p)