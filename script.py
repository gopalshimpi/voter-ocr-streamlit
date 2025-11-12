import easyocr
import re
import pandas as pd
from pathlib import Path
import glob
import cv2
import os

# --- OCR Setup ---
reader = easyocr.Reader(['mr', 'en'], gpu=False)

MARATHI_MAP = str.maketrans('०१२३४५६७८९', '0123456789')
BOUNDARY_LABELS = r'(?:नांव|वडिलांचे\s*नाव|वडिलांचे|घर\s*क्रमांक|Plot|वय|लिंग)'

# --- Utility functions ---
def normalize_text(s: str) -> str:
    """Normalize Marathi digits and whitespace."""
    s = s.translate(MARATHI_MAP)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def normalize_voter_id(voter_id: str) -> str:
    """Fix common OCR mistakes in voter ID like 78C -> TBC or KOT -> KDT"""
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
    """Run OCR and return joined text."""
    res = reader.readtext(str(img_path))
    return " ".join([r[1] for r in res])

# --- Extract name accurately ---
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

# --- Smart field extraction ---
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
            if nums_before:
                seq = nums_before[-1].group(0)
            else:
                seq = nums[0].group(0)
        else:
            seq = nums[0].group(0)
    seq = re.sub(r'[,\.\s]', '', seq).strip()

    part_m = re.search(r'\b\d+/\d+/\d+\b', text)
    part = part_m.group(0) if part_m else ""

    name = extract_name_by_label(text)
    if not name:
        name = extract_name_fallback(text)

    father_name = extract_father_name(text)

    return {
        "क्रमांक": seq,
        "मतदार ओळख क्रमांक": voter_id,
        "भाग क्रमांक": part,
        "मतदाराचे पूर्ण": name,
        "वडिलांचे नाव": father_name
    }

# --- Dynamic photo extraction ---
def extract_photo_dynamic(box_path: str, output_dir="photos"):
    os.makedirs(output_dir, exist_ok=True)
    img = cv2.imread(str(box_path))
    if img is None:
        return ""

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))

    if len(faces) == 0:
        # fallback: assume photo is right side of image
        h, w = img.shape[:2]
        x1 = int(w * 0.78)
        x2 = w - 5
        photo = img[:, x1:x2]
    else:
        # choose largest face region
        x, y, w_f, h_f = max(faces, key=lambda f: f[2] * f[3])
        pad = 15
        x1 = max(x - pad, 0)
        y1 = max(y - pad, 0)
        x2 = min(x + w_f + pad, img.shape[1])
        y2 = min(y + h_f + pad, img.shape[0])
        photo = img[y1:y2, x1:x2]

    photo_name = Path(box_path).stem + "_photo.png"
    photo_path = Path(output_dir) / photo_name
    cv2.imwrite(str(photo_path), photo)
    return str(photo_path)

# --- Single Image Processing ---
def process_image(img_path: str):
    print(f"\n🖼 Processing: {img_path}")
    raw = ocr_text(img_path)
    print("🧠 OCR Text:\n", raw)
    fields = extract_fields(raw)
    photo_path = extract_photo_dynamic(img_path)
    fields["photo_path"] = photo_path
    print("\n✅ Extracted Voter Info:")
    for k, v in fields.items():
        print(f"{k}: {v}")
    return fields

# --- Folder Processing ---
def process_folder(folder: str, out_csv="voter_list.csv"):
    files = sorted(glob.glob(str(Path(folder) / "*.png")))
    if not files:
        print(f"⚠️ No PNG images found in {folder}")
        return
    all_data = []
    for f in files:
        all_data.append({**process_image(f), "source_file": Path(f).name})
    pd.DataFrame(all_data).to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\n💾 Saved combined voter data to {out_csv}")

# --- Main ---
if __name__ == "__main__":
    single_img = Path("box1.png")
    if single_img.exists():
        data = process_image(str(single_img))
        pd.DataFrame([data]).to_csv("voter_info.csv", index=False, encoding="utf-8-sig")
        print("\n💾 Saved to voter_info.csv")
    elif Path("boxes").exists():
        process_folder("boxes")
    elif Path("voter_boxes_fixed").exists():
        process_folder("voter_boxes_fixed", out_csv="voter_boxes_fixed_output.csv")
    else:
        print("⚠️ Place 'box1.png' or a folder named 'boxes' or 'voter_boxes_fixed' next to this script.")
