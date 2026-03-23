import re

def simplify_log(text: str) -> str:
    """
    对日志进行简化：
    - 只在文本包含 'Process completed with exit code 0' 时执行
    - 保留所有现有 pip 和 uv 规则
    """
    # 如果不包含 exit code 0，则直接返回原文
    if "Process completed with exit code 0" not in text:
        return text.strip()

    # ------------------------
    # pip_simplify 原有规则
    # ------------------------
    pip_rules = [
        # 1. Using cached xxx-x.y.z-*.whl.metadata (xx kB)
        (
            r"Using cached ([^\s]+)-([0-9][^\s]*)-[^\s]+\.whl\.metadata \([^)]+\)",
            r"Using cached \1==\2 [whl]"
        ),
        # 2. Requirement already satisfied: pkg in path (from xxx)
        (
            r"Requirement already satisfied: ([^ ]+) in [^\n]+ \(from ([^)]+)\)",
            r"Requirement already satisfied: \1"
        ),
        # 3. Collecting xxx (from a->b->c)
        (
            r"^Collecting ([^ ]+)(?: \(from [^)]+\))?$",
            r"Collecting \1"
        ),
        # 4. manylinux label
        (
            r"manylinux_[0-9_]+_x86_64(\.manylinux_[0-9_]+_x86_64)*",
            r"[manylinux]"
        ),
        # 5. python tag / abi tag（eg. cp312-cp312）
        (
            r"cp[0-9]{2,3}-cp[0-9]{2,3}",
            r"[cp]"
        ),
        # 6. venv site-packages path
        (
            r"\./\.venv/lib/python[0-9.]+/site-packages",
            r"[venv]"
        ),
        # 7. metadata
        (
            r"\s*\(\d+(\.\d+)?\s*kB\)",
            r""
        ),
        # 8. Downloading bar
        (
            r"^\s*[━]+.*(kB/s|MB/s).*eta.*$",
            r""
        ),
        # 9. 其他下载 / 构建 / 进度噪声
        (
            r'^\s*(Downloading|Downloaded|Building|Built|Using cached|Installing|Getting|Preparing|Looking in|Collecting|Requirement already satisfied|Attempting uninstall|Found existing installation|Uninstalling|Successfully uninstalled|Updating|Updated).*$',
            r""
        ),
    ]

    simplified = text
    for pattern, replacement in pip_rules:
        simplified = re.sub(pattern, replacement, simplified, flags=re.MULTILINE)

    # ------------------------
    # uv_simplify 原有规则
    # ------------------------
    NOISE = re.compile(r'^\s*(Downloading|Downloaded|Building|Built|\+\s+|\-\s+).*$',
                       re.MULTILINE)
    
    simplified = NOISE.sub("", simplified)

    # ------------------------
    # 合并多行空行
    # ------------------------
    simplified = re.sub(r"\n{3,}", "\n\n", simplified).strip()

        # 匹配文件名
    file_pattern = re.compile(
        r'^[\s\-d]*[\-d][rwx\-]+.*?\s+([^\s]+)$',
        re.MULTILINE
    )

    def replace_ls_line(match):
        # match.group(1) 是文件名
        return match.group(1)

    simplified = file_pattern.sub(replace_ls_line, simplified)

    return simplified

if __name__ == "__main__":
    with open("log_file/test.log", 'r', encoding='utf-8') as f:
        text = f.read().strip()

    simplified_text = simplify_log(text)

    with open('log_file/test_result.log', 'w', encoding='utf-8') as f:
        f.write(simplified_text)