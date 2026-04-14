#!/usr/bin/env python3
"""
Parse MCP server deployment logs and export a CSV summary.

Usage:
    python parse_deploy_log.py <log_file> [output.csv]
"""

import re
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


# Patterns
RE_DEALING = re.compile(
    r"^[\d\-:, ]+ - INFO - Dealing with (\d+) .*/(\d+_.*?)_README\.md"
)
RE_TURN_START = re.compile(r"--- Communicate Count: (\d+) ---")
RE_TOKEN_USAGE = re.compile(r"Token Usage: (\{.*\})")
RE_TOOL_CALL = re.compile(
    r"\[Call Tool\] Server: MCP-Auto, Tool: (\w+), Args: (\{.*\})"
)
RE_TASK_DONE = re.compile(r"✅ @@Task Done@@")
RE_TASK_FAILED = re.compile(r"❌ @@Task Failed@@")


def parse_log_file(log_path):
    """Parse log file and return list of deployment records."""
    deployments = []
    current_deployment = None
    current_turn = None

    with open(log_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            # Check for new deployment start
            match_deal = RE_DEALING.search(line)
            if match_deal:
                # Finish previous deployment if any
                if current_deployment is not None:
                    finalize_deployment(current_deployment, "truncated")
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
                continue  # Haven't started a deployment block yet

            # Check for task completion markers
            if RE_TASK_DONE.search(line):
                current_deployment["final_status"] = "Task Done"
                continue
            if RE_TASK_FAILED.search(line):
                current_deployment["final_status"] = "Task Failed"
                continue

            # Check for turn start
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

            # If we are inside a turn, look for token usage and tool calls
            if current_turn is not None:
                # Token usage line
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

                # Tool call line
                match_tool = RE_TOOL_CALL.search(line)
                if match_tool:
                    tool_name = match_tool.group(1)
                    current_turn["tools"].append(tool_name)
                    continue

        # End of file: finalize last deployment
        if current_deployment is not None:
            if current_deployment["final_status"] is None:
                finalize_deployment(current_deployment, "truncated")
            deployments.append(current_deployment)

    return deployments


def finalize_deployment(deployment, status):
    """Set final status and ensure all turns are properly closed."""
    deployment["final_status"] = status


def deployments_to_csv(deployments, output_path):
    """Write deployments data to CSV."""
    fieldnames = [
        "repo_id",
        "full_name",
        "final_status",
        "turn_number",
        "tools_called",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for dep in deployments:
            repo_id = dep["repo_id"]
            full_name = dep["full_name"]
            final_status = dep["final_status"]

            # If no turns recorded, still output one row with empty turn data
            if not dep["turns"]:
                writer.writerow({
                    "repo_id": repo_id,
                    "full_name": full_name,
                    "final_status": final_status,
                    "turn_number": "",
                    "tools_called": "",
                    "prompt_tokens": "",
                    "completion_tokens": "",
                    "total_tokens": "",
                })
            else:
                for turn in dep["turns"]:
                    tools_str = ";".join(turn["tools"]) if turn["tools"] else ""
                    writer.writerow({
                        "repo_id": repo_id,
                        "full_name": full_name,
                        "final_status": final_status,
                        "turn_number": turn["turn_number"],
                        "tools_called": tools_str,
                        "prompt_tokens": turn["prompt_tokens"] or "",
                        "completion_tokens": turn["completion_tokens"] or "",
                        "total_tokens": turn["total_tokens"] or "",
                    })


def main():

    log_dir = "/home/silimon/mcp-auto/log_file"

    from dataset_setting import dataset_name

    log_file = log_dir + f'/EXP_{dataset_name}_14_44_2026-04-14_16-27-10.log'

    output_file = log_dir + f'/EXP_{dataset_name}_summary.log'

    print(f"Parsing {log_file} ...")
    deployments = parse_log_file(log_file)
    print(f"Found {len(deployments)} deployment records.")
    deployments_to_csv(deployments, output_file)
    print(f"CSV written to {output_file}")


if __name__ == "__main__":
    main()