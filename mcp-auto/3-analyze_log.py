#!/usr/bin/env python3
"""
Parse MCP server deployment logs and export a structured text log.

Usage:
    python parse_deploy_log.py <log_file> [output.log]
"""

import re
import json
import sys
from pathlib import Path

# 正则表达式
RE_DEALING = re.compile(
    r"^[\d\-:, ]+ - INFO - Dealing with (\d+) .*/(\d+_.*?)_README\.md"
)
RE_TURN_START = re.compile(r"--- Communicate Count: (\d+) ---")
RE_TOKEN_USAGE = re.compile(r"Token Usage: (\{.*\})")
RE_TOOL_CALL = re.compile(
    r"\[Call Tool\] Server: MCP-Auto, Tool: (\w+), Args: (\{.*\})"
)
# 允许前后空白，增强匹配
RE_TASK_DONE = re.compile(r"\s*@@Task Done@@\s*")
RE_TASK_FAILED = re.compile(r"\s*@@Task Failed@@\s*")


def parse_log_file(log_path):
    """解析日志文件，返回部署记录列表。"""
    deployments = []
    current_deployment = None
    current_turn = None

    with open(log_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            # 新部署开始
            match_deal = RE_DEALING.search(line)
            if match_deal:
                # 完成上一个部署（若存在且未完成）
                if current_deployment is not None:
                    # 如果没有明确的状态标记，视为失败
                    if current_deployment["final_status"] is None:
                        finalize_deployment(current_deployment, "Task Failed")
                    deployments.append(current_deployment)

                repo_id = match_deal.group(1)
                full_name = match_deal.group(2)
                current_deployment = {
                    "repo_id": repo_id,
                    "full_name": full_name,
                    "final_status": None,
                    "turns": [],
                }
                current_turn = None
                continue

            if current_deployment is None:
                continue  # 还未进入任何部署块

            # 任务完成/失败标记
            if RE_TASK_DONE.search(line):
                current_deployment["final_status"] = "Task Done"
                continue
            if RE_TASK_FAILED.search(line):
                current_deployment["final_status"] = "Task Failed"
                continue

            # 新一轮对话开始
            match_turn = RE_TURN_START.search(line)
            if match_turn:
                turn_num = int(match_turn.group(1))
                current_turn = {
                    "turn_number": turn_num,
                    "tools": [],
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                }
                current_deployment["turns"].append(current_turn)
                continue

            # 如果处于某一轮中，提取 token 用量和工具调用
            if current_turn is not None:
                # Token 用量
                match_token = RE_TOKEN_USAGE.search(line)
                if match_token:
                    try:
                        token_data = json.loads(match_token.group(1))
                        current_turn["prompt_tokens"] = token_data.get("prompt_tokens")
                        current_turn["completion_tokens"] = token_data.get("completion_tokens")
                        current_turn["total_tokens"] = token_data.get("total_tokens")
                    except json.JSONDecodeError:
                        pass
                    continue

                # 工具调用
                match_tool = RE_TOOL_CALL.search(line)
                if match_tool:
                    tool_name = match_tool.group(1)
                    args_str = match_tool.group(2)
                    current_turn["tools"].append({
                        "tool": tool_name,
                        "args": args_str
                    })
                    continue

        # 文件结束，处理最后一个部署
        if current_deployment is not None:
            if current_deployment["final_status"] is None:
                finalize_deployment(current_deployment, "Task Failed")
            deployments.append(current_deployment)

    return deployments


def finalize_deployment(deployment, status):
    """设置部署的最终状态，仅在尚未设置时生效。"""
    if deployment["final_status"] is None:
        deployment["final_status"] = status


def deployments_to_log(deployments, output_path):
    """将部署记录写入可读文本日志。"""
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, dep in enumerate(deployments, 1):
            repo_id = dep["repo_id"]
            full_name = dep["full_name"]
            status = dep["final_status"] or "unknown"
            turns = dep["turns"]
            total_turns = len(turns)

            f.write("=" * 80 + "\n")
            f.write(f"部署 #{idx}: {repo_id} ({full_name})\n")
            f.write(f"最终状态: {status}\n")
            f.write(f"对话总轮数: {total_turns}\n\n")

            if not turns:
                f.write("（无对话记录）\n\n")
                continue

            for turn in turns:
                turn_num = turn["turn_number"]
                tools = turn["tools"]
                pt = turn["prompt_tokens"] or "N/A"
                ct = turn["completion_tokens"] or "N/A"
                tt = turn["total_tokens"] or "N/A"

                f.write(f"--- 第 {turn_num} 轮 ---\n")
                f.write(f"Token 用量: prompt={pt}, completion={ct}, total={tt}\n")

                if tools:
                    f.write("调用的工具:\n")
                    for t in tools:
                        tool_name = t["tool"]
                        args = t["args"]
                        try:
                            args_obj = json.loads(args)
                            args_fmt = json.dumps(args_obj, ensure_ascii=False, indent=2)
                            f.write(f"  - {tool_name}:\n{args_fmt}\n")
                        except json.JSONDecodeError:
                            f.write(f"  - {tool_name}: {args}\n")
                else:
                    f.write("本轮无工具调用\n")
                f.write("\n")
            f.write("\n")

    print(f"文本日志已写入: {output_path}")


def main():
    # 日志文件路径（请根据实际情况修改）
    log_dir = "/home/silimon/mcp-auto/log_file"

    # 假设 dataset_setting 模块可用，否则直接指定文件名
    try:
        from dataset_setting import dataset_name
    except ImportError:
        dataset_name = "default"

    from glob import glob
    import os
    log_file = sorted(
        glob(os.path.join(log_dir, f"EXP_{dataset_name}_*.log")),
        # reverse=True
    )

    print(f"解析日志: {log_file} ...")
    for log in log_file:
        deployments = parse_log_file(log)
        print(f"共发现 {len(deployments)} 个部署记录。")
        output_file = log.replace('EXP_', 'EXP_summary_')
        deployments_to_log(deployments, output_file)


if __name__ == "__main__":
    main()