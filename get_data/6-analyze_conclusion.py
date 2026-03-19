import csv
import re
import os
from glob import glob
from dataset_setting import dataset_name


import re

def parse_log(log_file):
    results = {}

    current_name = None

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            m = re.search(r'Process file: .*?/([^/]+)_README\.md', line)
            if m:
                current_name = m.group(1)
                # default set No
                results[current_name] = "N"
                continue

            if current_name is None:
                continue

            if "Conclusion: @Yes@" in line or "结论: @Yes@" in line:
                results[current_name] = "Y"
            elif "Conclusion: @No@" in line or "结论: @No@" in line:
                results[current_name] = "N"

    return results


def extract_model_name(log_path):
    base = os.path.basename(log_path)
    m = re.search(r'classify_.*?_(.*?)_\d+\.log', base)
    if m:
        return m.group(1)
    return base


def analyze_logs(log_files, output_csv):

    all_results = {}
    models = []

    for log_file in log_files:

        model_name = extract_model_name(log_file)
        models.append(model_name)

        log_results = parse_log(log_file)

        for name, result in log_results.items():

            if name not in all_results:
                all_results[name] = {}

            all_results[name][model_name] = result

    # CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        header = ["name"] + models + ["vote"]
        writer.writerow(header)

        for name in sorted(all_results.keys()):

            row = [name]
            model_results = []

            for model in models:
                r = all_results[name].get(model, "")
                row.append(r)
                model_results.append(r)

            # vote
            unique_results = set(model_results)

            if len(unique_results) == 1:
                vote = unique_results.pop()
            else:
                vote = "conflict"

            row.append(vote)

            writer.writerow(row)

    print(f"Done. There are {len(all_results)} data -> {output_csv}")


if __name__ == "__main__":

    log_dir = "log_file/get_data"

    log_files = sorted(
        glob(os.path.join(log_dir, dataset_name, "classify_*"))
    )

    output_csv = f"data/dataset/{dataset_name}/{dataset_name}_model_compare.csv"

    analyze_logs(log_files, output_csv)