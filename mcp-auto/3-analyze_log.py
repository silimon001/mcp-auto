from __future__ import annotations

import re
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse, unquote
import ast


# ----------------------------
# 1) 正则
# ----------------------------
SEGMENT_START_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}.*? - INFO - Dealing with .*?$",
    re.MULTILINE,
)

COMMUNICATE_RE = re.compile(r"Communicate Count:\s*(\d+)")
TOKEN_USAGE_RE = re.compile(r"Token Usage:\s*(\{.*\})")
CALL_TOOL_RE = re.compile(
    r"\[Call Tool\]\s*Server:\s*.*?,\s*Tool:\s*(.*?),\s*Args:\s*(\{.*\})"
)

STATUS_PATTERNS = [
    (
        re.compile(r"❌\s*\**\s*@@Task Failed@@\s*\**"),
        "❌ @@Task Failed@@"
    ),

    (
        re.compile(r"\**\s*@@Task Alert@@\s*\**"),
        "⚠️ @@Task Alert@@"
    ),

    (
        re.compile(r"✅\s*\**\s*@@Task Done@@\s*\**"),
        "✅ @@Task Done@@"
    ),
]


# ----------------------------
# 2) 数据结构
# ----------------------------
@dataclass
class RoundRecord:
    round_id: int

    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    tool_calls: list[str] = field(default_factory=list)


@dataclass
class SegmentRecord:
    server_name: str
    status: str
    rounds: list[RoundRecord] = field(default_factory=list)


# ----------------------------
# 3) 工具函数
# ----------------------------
def _read_source_text(source: str) -> tuple[str, str | None]:
    """
    读取输入源文本。
    支持：
    - 本地路径
    - file:// URL
    - http(s) URL（先下载到临时文件再读取）
    返回：
    - text
    - local_path: 若可定位到本地路径则返回，否则为 None
    """
    parsed = urlparse(source)

    # file:// URL
    if parsed.scheme == "file":
        local_path = Path(unquote(parsed.path))
        return local_path.read_text(encoding="utf-8", errors="replace"), str(local_path)

    # http(s) URL
    if parsed.scheme in {"http", "https"}:
        with urllib.request.urlopen(source) as resp:
            raw = resp.read()
        text = raw.decode("utf-8", errors="replace")

        # 远程日志没有原始本地目录，这里返回 None，输出会落到当前目录下的同名 .log
        return text, None

    # 普通本地路径
    local_path = Path(source)
    return local_path.read_text(encoding="utf-8", errors="replace"), str(local_path)

def _parse_token_usage(token_usage_str: str) -> tuple[int, int, int]:
    """
    从 Token Usage JSON 字符串中提取：
    - prompt_tokens -> input
    - completion_tokens -> output
    - reasoning_tokens -> reasoning
    """
    try:
        data = ast.literal_eval(token_usage_str)

        output_tokens = data.get("completion_tokens", 0)
        input_tokens = data.get("prompt_tokens", 0)

        reasoning_tokens = (
            data.get("completion_tokens_details", {})
            .get("reasoning_tokens", 0)
        )

        return input_tokens, output_tokens, reasoning_tokens

    except Exception:
        return 0, 0, 0

def _output_path_for_source(source: str, local_path: str | None) -> Path:
    """
    生成输出路径：
    - 本地文件 / file://：
        同目录下生成：
        s_<原文件名>.slog

    - http(s) URL：
        当前目录下生成：
        s_<原文件名>.slog
    """

    if local_path is not None:
        p = Path(local_path)

        return p.with_name(
            f"s_{p.stem}.slog"
        )

    # 远程 URL
    parsed = urlparse(source)

    base = Path(unquote(parsed.path)).stem or "simplified"

    return Path.cwd() / f"s_{base}.slog"


def _extract_server_name(segment_text: str) -> str:
    """
    从 "Dealing with ..." 这一段里提取 MCP 服务器名称。
    示例：
    ... Dealing with 985428812 /home/.../985428812_google-pse-mcp_README.md ...
    -> 985428812_google-pse-mcp
    """
    first_line = segment_text.splitlines()[0].strip()

    # 优先抓 README 文件名
    m = re.search(r"/([^/\s]+)_README\.md\b", first_line)
    if m:
        return m.group(1)

    # 兜底：抓最后一个路径组件
    m = re.search(r"/([^/\s]+)\s*\.\.\.\s*$", first_line)
    if m:
        name = m.group(1)
        if name.endswith("_README.md"):
            return name[:-len("_README.md")]
        return name

    return "unknown_server"


def _extract_status(segment_text: str) -> str:
    """
    取该段落里最后一个状态标志。
    若完全没有任何标志，则按失败处理。
    """
    found: list[tuple[int, str]] = []
    for regex, normalized in STATUS_PATTERNS:
        for m in regex.finditer(segment_text):
            found.append((m.start(), normalized))

    if not found:
        return "❌ @@Task Failed@@"

    found.sort(key=lambda x: x[0])
    return found[-1][1]


def _split_segments(text: str) -> list[str]:
    """
    按每个 "Dealing with" 起始行切段。
    """
    starts = [m.start() for m in SEGMENT_START_RE.finditer(text)]
    if not starts:
        return []

    starts.append(len(text))
    segments = []
    for i in range(len(starts) - 1):
        seg = text[starts[i]:starts[i + 1]].strip()
        if seg:
            segments.append(seg)
    return segments


def _parse_rounds(segment_text: str) -> list[RoundRecord]:
    """
    解析一个 MCP 服务器测试段中的所有对话轮次。
    规则：
    - 每次出现 "Communicate Count: N" 视作新一轮开始
    - 该轮内抓取：
      - Token Usage
      - [Call Tool] 行
    """
    rounds: list[RoundRecord] = []
    current: RoundRecord | None = None

    for line in segment_text.splitlines():
        line = line.rstrip()

        m = COMMUNICATE_RE.search(line)
        if m:
            if current is not None:
                rounds.append(current)
            current = RoundRecord(round_id=int(m.group(1)))
            continue

        if current is None:
            continue

        m = TOKEN_USAGE_RE.search(line)
        if m:
            token_usage_str = m.group(1).strip()

            (
                current.input_tokens,
                current.output_tokens,
                current.reasoning_tokens,
            ) = _parse_token_usage(token_usage_str)

            continue

        if "[Call Tool]" in line:
            m = CALL_TOOL_RE.search(line)

            if m:
                tool, args = m.groups()

                current.tool_calls.append(
                    f"Tool={tool.strip()}, Args={args.strip()}"
                )

            else:
                current.tool_calls.append(line.strip())

    if current is not None:
        rounds.append(current)

    return rounds


def simplify_log_text(text: str) -> list[SegmentRecord]:
    """
    将一个原始日志文本，解析成结构化段落。
    """
    segments = _split_segments(text)
    results: list[SegmentRecord] = []

    for seg in segments:
        server_name = _extract_server_name(seg)
        status = _extract_status(seg)
        rounds = _parse_rounds(seg)
        results.append(SegmentRecord(server_name=server_name, status=status, rounds=rounds))

    return results


def write_simplified_log(records: list[SegmentRecord], output_path: Path) -> None:
    """
    写出简化日志。
    格式：
    MCP服务器名称 | 任务状态标志
    对话轮次1 | token usage | tool_calls
    ...
    """
    lines: list[str] = []

    for seg in records:
        lines.append(f"{seg.server_name} | {seg.status}")
        for rd in seg.rounds:
            
            token_usage = (
                f"input={rd.input_tokens}, "
                f"output={rd.output_tokens}, "
                f"reasoning={rd.reasoning_tokens}"
            )

            tool_calls = (
                " ; ".join(rd.tool_calls)
                if rd.tool_calls
                else "无 tool_calls"
            )

            lines.append(
                f"loop {rd.round_id} | "
                f"{token_usage} | "
                f"{tool_calls}"
            )

        lines.append("")  # 段落间空行

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def simplify_logs(log_sources: list[str]) -> list[Path]:
    """
    传入多个日志文件 URL / 路径，逐个生成对应的简化日志文件。
    返回生成的输出路径列表。
    """
    output_paths: list[Path] = []

    for source in log_sources:
        text, local_path = _read_source_text(source)
        records = simplify_log_text(text)
        output_path = _output_path_for_source(source, local_path)
        write_simplified_log(records, output_path)
        output_paths.append(output_path)

    return output_paths


# ----------------------------
# 4) CLI 示例
# ----------------------------
if __name__ == "__main__":
    log_sources: list[str] = [
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/0_40_2026-05-08_11-46-36.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/0_40_2026-05-08_18-47-24.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/160_200_2026-05-09_14-06-16.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/40_80_2026-05-08_17-36-02.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/80_120_2026-05-08_15-23-20.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/80_120_2026-05-08_23-57-08.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/0_40_2026-05-08_15-56-48.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/120_160_2026-05-09_12-51-47.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/40_80_2026-05-08_14-16-18.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/40_80_2026-05-08_18-37-34.log",
        "log_file/js_ts/MCP-Auto/qwen3.5-plus/80_120_2026-05-08_21-38-40.log"
    ]

    outputs = simplify_logs(log_sources)
    for p in outputs:
        print(f"written: {p}")