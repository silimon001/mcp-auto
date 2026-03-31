import os
import shutil
from dataset_setting import dataset_name

dataset_path = "data/dataset/" + dataset_name
simplified_readme_path = dataset_path + '/simplified_readme'
validated_readme_path = dataset_path + '/sampled_validated_readme'

import random

md_files = []
for root, dirs, files in os.walk(validated_readme_path):
    for file in files:
        if file.endswith(".md"):
            md_files.append(os.path.join(root, file))

num_samples = min(20, len(md_files))

# sampling
random.seed(2026)
readme_files = random.sample(md_files, num_samples)

import shutil

sampled_validated_readme_path = dataset_path + '/cline'
os.makedirs(sampled_validated_readme_path, exist_ok=True)

for file_path in readme_files:
    file_name = os.path.basename(file_path)
    target_path = os.path.join(sampled_validated_readme_path, file_name)

    shutil.copy2(file_path, target_path)


