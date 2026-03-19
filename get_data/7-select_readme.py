import os
import shutil
from dataset_setting import dataset_name

dataset_path = "data/dataset/" + dataset_name
simplified_readme_path = dataset_path + '/simplified_readme'

os.makedirs(f'{dataset_path}/validated_readme', exist_ok=True)
os.makedirs(f'{dataset_path}/conflict_readme', exist_ok=True)

with open(f'{dataset_path}/{dataset_name}_model_compare.csv', 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()[1:]  # skip header

for line in lines:
    readme_path = f"{dataset_path}/readme/" + line.split(',')[0] + "_README.md"
    if line.strip().split(',')[-1] == 'Y':
        id = line.split(',')[0].split('_')[0]
        shutil.copy2(readme_path, f"{dataset_path}/validated_readme/{line.split(',')[0]}_README.md")          
    elif line.strip().split(',')[-1] == 'conflict':
        shutil.copy2(readme_path, f"{dataset_path}/conflict_readme/{line.split(',')[0]}_README.md")



dataset_path = "data/dataset/" + dataset_name
validated_readme_path = dataset_path + '/validated_readme'

import random

md_files = []
for root, dirs, files in os.walk(validated_readme_path):
    for file in files:
        if file.endswith(".md"):
            md_files.append(os.path.join(root, file))

num_samples = min(200, len(md_files))

# sampling
random.seed(42)
readme_files = random.sample(md_files, num_samples)

import shutil

sampled_validated_readme_path = dataset_path + '/sampled_validated_readme'
os.makedirs(sampled_validated_readme_path, exist_ok=True)

for file_path in readme_files:
    file_name = os.path.basename(file_path)
    target_path = os.path.join(sampled_validated_readme_path, file_name)

    shutil.copy2(file_path, target_path)


