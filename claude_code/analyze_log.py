import os
import re
import sys
from collections import OrderedDict


def check_success(turns):
    """判断任务是否成功"""
    server_start_pattern = re.compile(
        r'\[OK\] The server .+ started successfully, tools:'
    )
    server_started = False
    for turn_num in sorted(turns.keys()):
        turn = turns[turn_num]
        # 检查是否服务器启动
        if not server_started:
            for result in turn.get('tool_results', []):
                if server_start_pattern.search(result):
                    server_started = True
                    break
        # 启动后才检查任务完成标志
        if server_started:
            for text in turn.get('assistant_texts', []):
                if '✅ @@Task Done@@' in text:
                    return True
    return False


def parse_session(session_text):
    """逐行解析一个会话，返回 turns, token_usage, status_line"""
    lines = session_text.splitlines()
    turns = OrderedDict()
    token_usage = {
        'input_tokens': '',
        'output_tokens': '',
        'cache_creation_input_tokens': '',
        'cache_read_input_tokens': ''
    }
    status_line = ""
    turn_num = 0
    i = 0

    def init_turn(num):
        if num not in turns:
            turns[num] = {
                'tool_calls': [],
                'tool_results': [],
                'assistant_texts': []
            }

    while i < len(lines):
        line = lines[i]

        # 1. 提取 Turn 编号
        m_turn = re.match(r'^\[Turn (\d+)\]', line)
        if m_turn:
            turn_num = int(m_turn.group(1))
            init_turn(turn_num)

        # 2. TOOL_CALL 行
        if 'TOOL_CALL' in line:
            init_turn(turn_num)
            if i + 1 < len(lines):
                tool_line = lines[i + 1].strip()
                m_tool = re.match(r'tool=([^,]+),\s*args=(.+)', tool_line)
                if m_tool:
                    turns[turn_num]['tool_calls'].append({
                        'tool': m_tool.group(1),
                        'args': m_tool.group(2)
                    })
                i += 2
            else:
                i += 1
            continue

        # 3. TOOL_RESULT 块（修正：使用子串匹配，不要求整行相等）
        if 'TOOL_RESULT' in line:
            init_turn(turn_num)
            result_lines = []
            i += 1
            while i < len(lines):
                l = lines[i]
                if (re.match(r'^\[Turn \d+\]', l) or
                    'TOOL_CALL' in l or
                    'ASSISTANT_TEXT' in l or
                    'TOOL_RESULT' in l or
                    'ASSISTANT_THINKING' in l or
                    'SESSION_INIT' in l or
                    'TOKEN USAGE' in l):
                    break
                result_lines.append(l)
                i += 1
            turns[turn_num]['tool_results'].append('\n'.join(result_lines))
            continue

        # 4. ASSISTANT_TEXT 块（不含 THINKING）
        if 'ASSISTANT_TEXT' in line and 'ASSISTANT_THINKING' not in line:
            init_turn(turn_num)
            text_lines = []
            i += 1
            while i < len(lines):
                l = lines[i]
                if (re.match(r'^\[Turn \d+\]', l) or
                    'TOOL_CALL' in l or
                    'ASSISTANT_TEXT' in l or
                    'TOOL_RESULT' in l or
                    'ASSISTANT_THINKING' in l or
                    'SESSION_INIT' in l or
                    'TOKEN USAGE' in l):
                    break
                text_lines.append(l)
                i += 1
            turns[turn_num]['assistant_texts'].append('\n'.join(text_lines))
            continue

        # 5. TOKEN USAGE 块（仅提取所需字段）
        if line.startswith('TOKEN USAGE:'):
            i += 1
            while i < len(lines):
                l = lines[i]
                if l.strip() == '':
                    i += 1
                    break
                for field in ['input_tokens', 'output_tokens',
                              'cache_creation_input_tokens', 'cache_read_input_tokens']:
                    m = re.match(r'\s*' + field + r':\s*(\d+)', l)
                    if m:
                        token_usage[field] = m.group(1)
                        break
                i += 1
            continue

        # 6. status 行
        m_status = re.match(r'^status=(.+)', line)
        if m_status:
            status_line = m_status.group(1).strip()
            i += 1
            continue

        i += 1

    return turns, token_usage, status_line


def process_log(filepath):
    dirname = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    out_filepath = os.path.join(dirname, "s_" + basename) if dirname else "s_" + basename

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按 SESSION_INIT 分割
    sessions = re.split(r'^\[.*?\] SESSION_INIT\s*\n', content, flags=re.MULTILINE)
    if not re.match(r'^\[.*?\] SESSION_INIT', content.split('\n')[0]):
        sessions = sessions[1:]

    session_idx = 0
    with open(out_filepath, 'w', encoding='utf-8') as fout:
        for session_text in sessions:
            if not session_text.strip():
                continue

            session_idx += 1
            turns, token_usage, status_line = parse_session(session_text)
            success = check_success(turns)
            flag = "✅ @@Task Done@@" if success else "❌ @@Task Failed@@"

            print(f"{session_idx} | {flag} | "
                  f"Input: {token_usage['input_tokens']} "
                  f"Output: {token_usage['output_tokens']} "
                  f"cache_creation: {token_usage['cache_creation_input_tokens']} "
                  f"cache_read: {token_usage['cache_read_input_tokens']}",
                  file=fout)

            for turn_num in sorted(turns.keys()):
                tool_calls = turns[turn_num].get('tool_calls', [])
                if tool_calls:
                    call_strs = [f"Tool={tc['tool']}, Args={tc['args']}" for tc in tool_calls]
                    print(f"loop {turn_num} | {'; '.join(call_strs)}", file=fout)
                else:
                    print(f"loop {turn_num} | 无 tool_calls", file=fout)
            print(file=fout)

if __name__ == '__main__':
    
    process_log('log_file/py/claude-code-1/qwen3.5-plus-2026-04-20/120_160_2026-06-10_09-49-24.log')