import easyocr
import re
import pandas as pd
from pathlib import Path
import glob
import cv2
import os
import time
import sys
import warnings

# Suppress unnecessary torch/easyocr warnings
warnings.filterwarnings("ignore", category=UserWarning)

# === OCR Setup ===
reader = easyocr.Reader(['mr', 'en'], gpu=False)

MARATHI_MAP = str.maketrans('०१२३४५६७८९', '0123456789')
BOUNDARY_LABELS = r'(?:नांव|वडिलांचे\s*नाव|वडिलांचे|घर\s*क्रमांक|Plot|वय|लिंग)'

# === Utility functions ===
def normalize_text(s: str) -> str:
    s = s.translate(MARATHI_MAP)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def normalize_voter_id(voter_id: str) -> str:
    if not voter_id:
        return ""
    v = voter_id.strip().upper()
    fixes = {
        "7BC": "TBC", "78C": "TBC", "I3C": "TBC", "IBC": "TBC", "T8C": "TBC",
        "KOT": "KDT", "K0T": "KDT", "K0D": "KDT", "KDI": "KDT", "KDC": "KDT",
        "TBD": "TBC"
    }
    for wrong, right in fixes.items():
        v = v.replace(wrong, right)
    return v

def ocr_text(img_path: str) -> str:
    res = reader.readtext(str(img_path))
    return " ".join([r[1] for r in res])

# === Extraction logic unchanged ===
def extract_name_by_label(text: str) -> str:
    label_variants = [
        r'मतदाराचे\s*पूर्ण\s*नांव[:：]?',
        r'मतदाराचे\s*पूर्ण[:：]?',
        r'मतदाराचे[:：]?',
        r'मतदार\s*पूर्ण[:：]?'
    ]
    pattern = re.compile("|".join(label_variants))
    m = pattern.search(text)
    if not m:
        return ""
    start = m.end()
    tail = text[start:]
    boundary = re.search(r'(?:\s|^)(' + BOUNDARY_LABELS + r')(?:\s|$)', tail)
    end = boundary.start() if boundary else len(tail)
    name = tail[:end].strip()
    name = re.sub(r'^[\s:：ः\-]+', '', name)
    name = re.sub(r'(नांव|वडिलांचे\s*नाव|घर\s*क्रमांक|वय|लिंग).*$', '', name)
    name = re.sub(r'[^-\u0900-\u097F\sA-Za-z]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def extract_name_fallback(text: str) -> str:
    boundary = re.search(BOUNDARY_LABELS, text)
    left = text[:boundary.start()] if boundary else text
    chunks = re.findall(r'[\u0900-\u097F\s]{3,}', left)
    if not chunks:
        return ""
    return max(chunks, key=lambda s: len(s.strip())).strip()

def extract_father_name(text: str) -> str:
    pattern = re.compile(r'(वडिलांचे\s*नाव|वडिलांचे|पतीचे\s*नाव|पतीचे)\s*[:：]?\s*([\u0900-\u097F\sA-Za-z]+)')
    match = pattern.search(text)
    if not match:
        return ""
    name = match.group(2).strip()
    name = re.split(r'(घर|क्रमांक|Plot|वय|लिंग)', name)[0]
    name = re.sub(r'[^-\u0900-\u097F\sA-Za-z]', '', name)
    return name.strip()

def extract_fields(raw_text: str):
    text = normalize_text(raw_text)
    num_pattern = re.compile(r'\b\d{1,3}(?:[,\.\s]?\d{3})*\b')
    nums = list(num_pattern.finditer(text))
    vid_m = re.search(r'\b[A-Z0-9]{2,}\d{3,}\b', text)
    voter_id = normalize_voter_id(vid_m.group(0)) if vid_m else ""

    seq = ""
    if nums:
        if vid_m:
            nums_before = [m for m in nums if m.start() < vid_m.start()]
            seq = nums_before[-1].group(0) if nums_before else nums[0].group(0)
        else:
            seq = nums[0].group(0)
    seq = re.sub(r'[,\.\s]', '', seq).strip()

    part_m = re.search(r'\b\d+/\d+/\d+\b', text)
    part = part_m.group(0) if part_m else ""
    name = extract_name_by_label(text) or extract_name_fallback(text)
    father_name = extract_father_name(text)

    return {
        "क्रमांक": seq,
        "मतदार ओळख क्रमांक": voter_id,
        "भाग क्रमांक": part,
        "मतदाराचे पूर्ण": name,
        "वडिलांचे नाव": father_name
    }

# === Dynamic photo extraction ===
def extract_photo_dynamic(box_path: str, output_dir="photos"):
    os.makedirs(output_dir, exist_ok=True)
    img = cv2.imread(str(box_path))
    if img is None:
        return ""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))

    if len(faces) == 0:
        h, w = img.shape[:2]
        x1, x2 = int(w * 0.78), w - 5
        photo = img[:, x1:x2]
    else:
        x, y, w_f, h_f = max(faces, key=lambda f: f[2] * f[3])
        pad = 15
        x1, y1 = max(x - pad, 0), max(y - pad, 0)
        x2, y2 = min(x + w_f + pad, img.shape[1]), min(y + h_f + pad, img.shape[0])
        photo = img[y1:y2, x1:x2]

    photo_name = Path(box_path).stem + "_photo.png"
    photo_path = Path(output_dir) / photo_name
    cv2.imwrite(str(photo_path), photo)
    return str(photo_path)

# === Progress Bar ===
def print_progress(current, total, bar_length=30):
    percent = current / total
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)
    sys.stdout.write(f"\rProgress: {percent*100:5.1f}% [{bar}]")
    sys.stdout.flush()

# === Image Processing ===
def process_image(img_path: str):
    raw = ocr_text(img_path)
    fields = extract_fields(raw)
    photo_path = extract_photo_dynamic(img_path)
    fields["photo_path"] = photo_path
    return fields

# === Folder Processing ===
def process_folder(folder: str, out_csv="voter_list.csv"):
    folder = Path(folder)
    files = sorted(folder.rglob("*.png"))
    if not files:
        print(f"⚠️ No PNG images found in {folder}")
        return

    total = len(files)
    print(f"\n📦 Found {total} voter box images in '{folder}'\n")

    all_data = []
    start_time = time.time()

    for i, f in enumerate(files, start=1):
        data = process_image(str(f))
        data["source_file"] = f.name
        all_data.append(data)

        # update progress bar cleanly (no newlines)
        print_progress(i, total)

    elapsed = time.time() - start_time
    print(f"\n\n💾 All done in {elapsed:.1f}s! Saving results...")
    pd.DataFrame(all_data).to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"✅ Saved {len(all_data)} records to {out_csv}\n")

# === Main ===
if __name__ == "__main__":
    input_folder = Path("voter_list_box")
    if input_folder.exists():
        process_folder(input_folder, out_csv="voter_list_output.csv")
    else:
        print("⚠️ Folder 'voter_list_box' not found. Please create it and put PNG images inside.")
