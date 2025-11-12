import easyocr
import re
import pandas as pd
from pathlib import Path
import glob

# --- OCR Setup ---
reader = easyocr.Reader(['mr', 'en'], gpu=False)

MARATHI_MAP = str.maketrans('०१२३४५६७८९', '0123456789')
BOUNDARY_LABELS = r'(?:नांव|वडिलांचे\s*नाव|वडिलांचे|घर\s*क्रमांक|Plot|वय|लिंग)'

# --- Utility functions ---
def normalize_text(s: str) -> str:
    s = s.translate(MARATHI_MAP)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def normalize_voter_id(voter_id: str) -> str:
    """Fix common OCR mistakes in voter ID like 78C -> TBC"""
    if not voter_id:
        return ""
    v = voter_id.strip().upper()
    fixes = {
        "7BC": "TBC", "78C": "TBC", "I3C": "TBC", "IBC": "TBC",
        "KOT": "KDT", "K0T": "KDT", "K0D": "KDT", "K0T": "KDT",
        "KOT": "KDT", "KDI": "KDT"
    }
    for wrong, right in fixes.items():
        v = v.replace(wrong, right)
    return v

def ocr_text(img_path: str) -> str:
    res = reader.readtext(img_path)
    return " ".join([r[1] for r in res])

# --- Extract name accurately ---
def extract_name_by_label(text: str) -> str:
    """Extracts voter's name after 'मतदाराचे पूर्ण' or 'मतदाराचे पूर्ण नांव'"""
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
    # stop at next boundary like नांव / वडिलांचे नाव / वय etc
    boundary = re.search(r'(?:\s|^)(' + BOUNDARY_LABELS + r')(?:\s|$)', tail)
    end = boundary.start() if boundary else len(tail)
    name = tail[:end].strip()
    # cleanup
    name = re.sub(r'^[\s:：ः\-]+', '', name)
    name = re.sub(r'(नांव|वडिलांचे\s*नाव|घर\s*क्रमांक|वय|लिंग).*$', '', name)
    name = re.sub(r'[^-\u0900-\u097F\sA-Za-z]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def extract_name_fallback(text: str) -> str:
    """Fallback: find longest Devanagari chunk before next label"""
    boundary = re.search(BOUNDARY_LABELS, text)
    left = text[:boundary.start()] if boundary else text
    chunks = re.findall(r'[\u0900-\u097F\s]{3,}', left)
    if not chunks:
        return ""
    return max(chunks, key=lambda s: len(s.strip())).strip()

# --- Field extraction ---
def extract_fields(raw_text: str):
    text = normalize_text(raw_text)

    # क्रमांक: first number before voter id
    nums = list(re.finditer(r'\b\d{1,3}(?:,\d{3})*\b', text))
    vid_m = re.search(r'\b[A-Z0-9]{2,}\d{3,}\b', text)
    voter_id = normalize_voter_id(vid_m.group(0)) if vid_m else ""

    seq = ""
    if nums:
        if vid_m:
            nums_before = [m for m in nums if m.start() < vid_m.start()]
            if nums_before:
                seq = nums_before[0].group(0)
            else:
                seq = nums[0].group(0)
        else:
            seq = nums[0].group(0)

    # भाग क्रमांक (e.g. 10/128/185)
    part_m = re.search(r'\b\d+/\d+/\d+\b', text)
    part = part_m.group(0) if part_m else ""

    # मतदाराचे पूर्ण (name)
    name = extract_name_by_label(text)
    if not name:
        # fallback if label not detected
        name = extract_name_fallback(text)

    return {
        "क्रमांक": seq,
        "मतदार ओळख क्रमांक": voter_id,
        "भाग क्रमांक": part,
        "मतदाराचे पूर्ण": name
    }

# --- Single Image Processing ---
def process_image(img_path: str):
    print(f"\n🖼 Processing: {img_path}")
    raw = ocr_text(img_path)
    print("🧠 OCR Text:\n", raw)
    fields = extract_fields(raw)
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
    else:
        print("⚠️ Place 'box1.png' or a folder named 'boxes' with voter box images next to this script.")
