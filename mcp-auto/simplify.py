import re

# pip

def pip_summary(text: str) -> str:
    success_markers = [
        "Successfully installed",
    ]

    has_success = any(m in text for m in success_markers)

    exit_code_match = re.search(r"Process completed with exit code (\d+)", text)
    exit_code_ok = (
        exit_code_match is None or exit_code_match.group(1) == "0"
    )

    if not (has_success and exit_code_ok):
        return text.strip()

    output = 'pip install completed successfully.'
    first_line = None
    second_line = None
    last_line = None
    time_line = None

    for line in text.splitlines():
        if line.startswith("Process started with PID"):
            first_line = line.strip()
        elif line.startswith("Initial output:"):
            second_line = line.strip()
        elif line.startswith("Process completed"):
            last_line = line.strip()
        elif line.startswith("Runtime:"):
            time_line = line.strip()

    return f"{first_line}\n{second_line}\n{output}\n{last_line}\n{time_line}"

def pip_simplify(text: str) -> str:
        rules = [
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

            (
                r'^\s*(Downloading|Downloaded|Building|Built|Using cached|Installing|Getting|Preparing|Looking in).*$',
                r""
            )
        ]

        simplified = text
        for pattern, replacement in rules:
            simplified = re.sub(pattern, replacement, simplified, flags=re.MULTILINE)

        simplified = re.sub(r"\n{3,}", "\n\n", simplified)

        return simplified.strip()


# uv

SUCCESS_PATTERN = re.compile(
    r"Process completed with exit code 0"
)

FAIL_EXIT_CODE_PATTERN = re.compile(
    r"Process completed with exit code (?!0)\d+"
)

FAIL_KEYWORD_PATTERN = re.compile(
    r"\b(error|failed|exception|traceback)\b",
    re.IGNORECASE,
)



def uv_success(output: str) -> bool:

    if SUCCESS_PATTERN.search(output):
        return True

    if FAIL_EXIT_CODE_PATTERN.search(output):
        return False

    if FAIL_KEYWORD_PATTERN.search(output):
        return False

    return False


UV_PATTERN = re.compile(
    r'^\s*(Downloading|Downloaded|Building|Built|\+\s+).*$',
    re.MULTILINE
)

def uv_simplify(output: str) -> str:

    if not uv_success(output):
        return output
    
    compressed = UV_PATTERN.sub("", output)
    
    compressed = re.sub(r"\n{3,}", "\n\n", compressed).strip()

    return compressed


if __name__ == "__main__":
    with open("log_file/test.log", 'r', encoding='utf-8') as f:
        text = f.read().strip()

    simplified_text = pip_simplify(text)
    simplified_text = uv_simplify(simplified_text)
    with open('log_file/test_result.log', 'w', encoding='utf-8') as f:
        f.write(simplified_text)