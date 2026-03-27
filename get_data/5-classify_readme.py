from dotenv import load_dotenv
load_dotenv('.mcp-auto_env')

import os
import glob
import logging
from openai import OpenAI
from dataset_setting import dataset_name


PROMPT_PATH = "get_data/prompt_5_classify_readme.md"
LOG_DIR = "log_file/get_data/{dataset}"
README_TEMPLATE = """Next is a README document that requires your judgment.

{content}
"""


def init_logger(path: str, model: str, thinking_budget: int, log_mode: str):
    dataset = path.split('/')[-2]
    log_dir = LOG_DIR.format(dataset=dataset)

    os.makedirs(log_dir, exist_ok=True)

    logger_name = f"{model}_{thinking_budget}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        log_file = os.path.join(
            log_dir,
            f"classify_{dataset}_{model}_{thinking_budget}.log"
        )
        handler = logging.FileHandler(log_file, mode=log_mode, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def build_messages(prompt: str, readme_content: str):
    return [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": README_TEMPLATE.format(content=readme_content)
        }
    ]


def call_qwen(
    client,
    model,
    messages,
    max_tokens,
    enable_thinking,
    thinking_budget
):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0,
        extra_body={
            "enable_thinking": enable_thinking,
            "thinking_budget": thinking_budget,
        },
    )


def call_deepseek_stream(
    client,
    model,
    messages,
    max_tokens,
    enable_thinking,
    thinking_budget,
    logger,
):
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0,
        extra_body={
            "enable_thinking": enable_thinking,
            "thinking_budget": thinking_budget,
        },
        stream=True,
    )

    reasoning_content = []
    answer_content = []
    is_answering = False

    print("\n" + "=" * 20 + "Thinking" + "=" * 20 + "\n")

    for chunk in completion:
        if not chunk.choices:
            print("\n" + "=" * 20 + "Token using" + "=" * 20 + "\n")
            print(chunk.usage)
            continue

        delta = chunk.choices[0].delta

        if getattr(delta, "reasoning_content", None):
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
            reasoning_content.append(delta.reasoning_content)

        if getattr(delta, "content", None):
            if not is_answering:
                print("\n" + "=" * 20 + "Response" + "=" * 20 + "\n")
                is_answering = True
            print(delta.content, end="", flush=True)
            answer_content.append(delta.content)

    final_answer = "".join(answer_content)
    logger.info(f"answer:\n{final_answer}\n")


def analyze_readme(
    path: str,
    files: list[str],
    model: str = "qwen-flash",
    log_mode: str = "a",
    enable_thinking: bool = False,
    start_index: int = 0,
    max_tokens: int = 5120,
    thinking_budget: int = 5120,
    upper_bound: int = 25000,
):
    client = OpenAI(
        api_key=os.getenv("QWEN_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        prompt = f.read()

    logger = init_logger(path, model, thinking_budget, log_mode)
    logger.info("Running")

    processed = start_index

    for readme_file in files[processed:]:
        logger.info(f"{processed} Process file: {readme_file}")

        try:
            with open(readme_file, "r", encoding="utf-8") as f:
                readme_content = f.read()

            messages = build_messages(prompt, readme_content)

            if model.startswith("qwen"):
                completion = call_qwen(
                    client,
                    model,
                    messages,
                    max_tokens,
                    enable_thinking,
                    thinking_budget,
                )
                logger.info(
                    f"answer:\n{completion.choices[0].message.content}\n"
                )

            elif model.startswith("deepseek"):
                call_deepseek_stream(
                    client,
                    model,
                    messages,
                    max_tokens,
                    enable_thinking,
                    thinking_budget,
                    logger,
                )

        except Exception as e:
            logger.exception(f"Process failed: {readme_file}")

        processed += 1
        if processed >= upper_bound:
            break

    logger.info("Done!")

if __name__ == "__main__":

    dataset_path = "data/dataset/" + dataset_name
    simplified_readme_path = dataset_path + '/simplified_readme'
    from glob import glob
    readme_files = sorted(
        glob(os.path.join(simplified_readme_path, "*.md")),
        key=os.path.getsize,
        # reverse=True
    )

    counts = 0

    model = 'qwen3.5-flash'
    analyze_readme(path=simplified_readme_path, files=readme_files, model=model, log_mode='w', enable_thinking=True, start_index=counts, max_tokens=512, thinking_budget=256, upper_bound=5000)
    model = 'qwen3.5-plus'
    analyze_readme(path=simplified_readme_path, files=readme_files, model=model, log_mode='w', enable_thinking=True, start_index=counts, max_tokens=512, thinking_budget=256, upper_bound=5000)
    model = 'deepseek-v3.2'
    analyze_readme(path=simplified_readme_path, files=readme_files, model=model, log_mode='w', enable_thinking=False, start_index=counts, max_tokens=512, thinking_budget=0, upper_bound=5000)
