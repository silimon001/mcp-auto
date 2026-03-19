import re
import os
from glob import glob
from dataset_setting import dataset_name

def clean_text(text):
    # 1. 删除HTML标签
    text = re.sub(r'<[^>]*>', '', text)

    # 2. 定义允许的字符集合（中文、日文、韩文、英文、数字、标点、代码符号、空格和换行）
    allowed_chars = (
        r"\u4e00-\u9fff"       # 中文
        r"\u3400-\u4dbf"       # 扩展中文
        r"\u3040-\u309f"       # 日文平假名
        r"\u30a0-\u30ff"       # 日文片假名
        r"\uac00-\ud7af"       # 韩文
        r"a-zA-Z0-9"            # 英文和数字
        r"！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～"  # 中文标点
        r"\.,:;!?(){}\[\]<>+=*/%&|^~!?\-_`@#$"  # 代码常用符号
        r"\s"                   # 空格和换行
    )

    # 3. 构建正则，匹配所有**不在允许集合中的字符**
    pattern = f"[^{allowed_chars}]"

    # 4. 删除不允许的字符
    text = re.sub(pattern, "", text)

    # 5. 合并多余空行
    text = re.sub(r'\n\s*\n', '\n\n', text)

    # 去除首尾空白
    return text.strip()

def clean_links(text: str) -> str:
    """
    清理 Markdown / HTML 链接，只保留显示文字。
    """

    # 1. 图片链接 ![alt](url) -> alt
    text = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', text)

    # 2. 普通 markdown 链接 [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)

    # 3. 引用式链接 [text][id] -> text
    text = re.sub(r'\[(.*?)\]\[[^\]]+\]', r'\1', text)

    # 4. 引用定义 [id]: url -> 删除整行
    text = re.sub(r'^\[[^\]]+\]:\s+\S+\s*$', '', text, flags=re.MULTILINE)

    # 5. HTML 链接 <a href="...">text</a> -> text
    text = re.sub(r'<a\s+href="[^"]*">(.*?)</a>', r'\1', text, flags=re.IGNORECASE)

    # 6. 裸 url -> 删除 / a link
    # text = re.sub(r'https?://[^\s)]+', '', text)
    text = re.sub(r'https?://[^\s)]+', 'a link', text)

    return text

if __name__ == '__main__':
    dataset_path = "data/dataset/" + dataset_name
    readme_path = dataset_path + '/readme'

    sampled_path = dataset_path + '/sampled_readme'
    os.makedirs(sampled_path, exist_ok=True)

    simplified_readme_path = dataset_path + '/simplified_readme'
    os.makedirs(simplified_readme_path, exist_ok=True)

    import random

    md_files = []
    for root, dirs, files in os.walk(readme_path):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))

    num_samples = min(200, len(md_files))
    num_samples = min(5000, len(md_files))

    # sampling
    random.seed(42)
    readme_files = random.sample(md_files, num_samples)

    import shutil

    for file_path in readme_files:
        file_name = os.path.basename(file_path)
        target_path = os.path.join(sampled_path, file_name)

        shutil.copy2(file_path, target_path)

    print(f"Simply random sample {len(readme_files)} README files and copy to {sampled_path}")

    print(len(readme_files), " readme files found for optimization.")

    for readme_file in readme_files:
        with open(readme_file, "r", encoding="utf-8") as f:
            content = f.read()
        simplified = clean_links(clean_text(content))
        with open(f'{simplified_readme_path}/{os.path.basename(readme_file)}', "w", encoding="utf-8", newline='\n') as f:
            f.write(simplified)
