import json
from collections import defaultdict, Counter
from datetime import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import math
import os

import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Noto Sans CJK JP"]
matplotlib.rcParams["axes.unicode_minus"] = False

from matplotlib import font_manager
fonts = sorted({f.name for f in font_manager.fontManager.ttflist})
for f in fonts:
    if "CJK" in f or "Hei" in f or "Song" in f:
        print(f)


raw_repos_info_path = "data/raw_repos_info/raw_repos_info.jsonl"
log_dir = "log_file/get_data"

data = []

with open(raw_repos_info_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        data.append(json.loads(line))

# stars_count
star_counter = Counter()

for item in data:
    stars = item.get("stars_count", 0)
    star_counter[stars] += 1

x = sorted(star_counter.keys())
y = [star_counter[k] for k in x]

plt.figure()
plt.plot(x, y, linewidth=1)
plt.xlabel("stars")
plt.ylabel("the number of repos")
plt.xscale('log')
plt.title("Distribution of GitHub repository stars")
plt.savefig(f"{os.getcwd()}/{log_dir}/stars_count.png", dpi=300)
plt.show()
plt.close()

# language
language_counter = Counter()

for item in data:
    lang = item.get("language")
    if lang is None:
        lang = "null"
    language_counter[lang] += 1

main_lang = {}
other_count = 0

for lang, cnt in language_counter.items():
    if cnt > 100:
        main_lang[lang] = cnt

sorted_items = sorted(
    main_lang.items(),
    key=lambda x: x[1], 
    reverse=True
)

x = [k for k, v in sorted_items]
y = [v for k, v in sorted_items]

plt.figure()
plt.bar(x, y)
plt.xlabel("language")
plt.ylabel("the number of repos")
plt.title("Distribution of GitHub repository languages")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(f"{os.getcwd()}/{log_dir}/language.png", dpi=300)
plt.show()
plt.close()

# size
size_counter = defaultdict(int)

for item in data:
    size = item.get("size", 0)  # KB
    bucket = size // 1024       # MB
    size_counter[bucket] += 1

x = [k for k in sorted(size_counter.keys()) if k > 0]
y = [size_counter[k] for k in x]

plt.figure()
plt.plot(x, y, linewidth=1)

plt.xlabel("size (MB)")
plt.ylabel("the number of repos")
plt.title("Distribution of GitHub repository sizes")

plt.xscale("log")

plt.savefig(f"{os.getcwd()}/{log_dir}/size.png", dpi=300)
plt.show()
plt.close()

# created time
from collections import Counter
from datetime import datetime
import os
import matplotlib.pyplot as plt

date_counter = Counter()
cutoff_date = datetime(2024, 11, 25)

for item in data:
    created_at = item.get("created_at")
    if not created_at:
        continue

    dt = datetime.fromisoformat(created_at.replace("Z", ""))

    if dt < cutoff_date:
        date_counter["before_2024-11"] += 1
    else:
        month_str = dt.strftime("%Y-%m")
        date_counter[month_str] += 1


x = sorted(
    date_counter.keys(),
    key=lambda k: (k != "before_2024-11", k)
)

y = [date_counter[k] for k in x]

from matplotlib.ticker import MaxNLocator

plt.figure()
plt.plot(x, y, linewidth=1)

plt.ylabel("the number of repos")
plt.xlabel("month")
plt.title("Distribution of GitHub repository created-time")

plt.gca().xaxis.set_major_locator(MaxNLocator(8))
plt.xticks(rotation=45, ha="right")

plt.tight_layout()
plt.savefig(f"{os.getcwd()}/{log_dir}/created_time.png", dpi=300)
plt.show()
plt.close()