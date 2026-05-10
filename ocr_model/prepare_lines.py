import os
import re
from collections import defaultdict

WORDS_TXT = r'C:\Users\Abhinav Chouhan\gradeops\ocr_data\iam_words\words.txt'
LINES_DIR = r'C:\Users\Abhinav Chouhan\gradeops\ocr_data\iam_lines'
OUTPUT_TXT = r'C:\Users\Abhinav Chouhan\gradeops\ocr_data\iam_lines\lines.txt'

def build_lines_labels():
    # Parse words.txt to group words by line
    # Word ID format: a01-000u-00-00
    # Line ID = a01-000u-00 (first 3 parts)
    line_words = defaultdict(list)

    with open(WORDS_TXT, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split(' ')
            if len(parts) < 9:
                continue
            word_id = parts[0]
            seg_result = parts[1]
            if seg_result == 'err':
                continue
            label = ' '.join(parts[8:])

            # Extract line ID from word ID
            id_parts = word_id.split('-')
            if len(id_parts) < 4:
                continue
            line_id = f"{id_parts[0]}-{id_parts[1]}-{id_parts[2]}"
            line_words[line_id].append((int(id_parts[3]), label))

    # Build lines labels and verify image exists
    valid_lines = []
    for line_id, words in line_words.items():
        # Sort words by position
        words.sort(key=lambda x: x[0])
        line_text = ' '.join(w[1] for w in words)

        # Build image path
        id_parts = line_id.split('-')
        img_path = os.path.join(
            LINES_DIR,
            id_parts[0],
            f"{id_parts[0]}-{id_parts[1]}",
            f"{line_id}.png"
        )

        if os.path.exists(img_path):
            valid_lines.append((img_path, line_text))

    print(f"Found {len(valid_lines)} valid line images with labels")

    # Write labels file
    with open(OUTPUT_TXT, 'w') as f:
        for img_path, text in valid_lines:
            f.write(f"{img_path}\t{text}\n")

    print(f"Labels written to {OUTPUT_TXT}")
    return valid_lines

if __name__ == '__main__':
    lines = build_lines_labels()
    if lines:
        print("\nSample lines:")
        for path, text in lines[:5]:
            print(f"  {os.path.basename(path)}: '{text}'")