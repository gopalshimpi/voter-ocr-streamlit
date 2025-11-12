# save as extract_voter_fixed.py
import re
import glob
import pandas as pd
import easyocr
from pathlib import Path

reader = easyocr.Reader(['mr', 'en'], gpu=False)

MARATHI_MAP = str.maketrans('०१२३४५६७८९', '0123456789')

# boundary labels that mark the end of the name and things to ignore
BOUNDARY_LABELS = r'(?:नांव|वडिलांचे\s*नाव|वडिलांचे|घर\s*क्रमांक|Plot|वय|लिंग)'

def normalize_text(s: str) -> str:
    s = s.strip()
    s = s.translate(MARATHI_MAP)
    s = re.sub(r'\s+', ' ', s)
    return s

def ocr_text(img_path: str) -> str:
    res = reader.readtext(img_path)
    # preserve reading order by joining in the returned order
    return " ".join([r[1] for r in res])

def extract_from_text(raw: str):
    text = normalize_text(raw)
    # --- find voter id first (so we can locate position) ---
    vid_match = re.search(r'\b([A-Z]{1,}\d{3,})\b', text)
    vid = vid_match.group(1) if vid_match else ""

    # --- find part/area like 10/128/185 ---
    part_match = re.search(r'\b(\d+/\d+/\d+)\b', text)
    part = part_match.group(1) if part_match else ""

    # --- find all numbers-with-commas (e.g., 1,386) and choose the one before voter id if possible ---
    num_iter = list(re.finditer(r'\b\d{1,3}(?:,\d{3})*\b', text))
    seq_num = ""
    if num_iter:
        if vid_match:
            # pick the first numeric occurrence that appears BEFORE voter-id
            nums_before_vid = [m for m in num_iter if m.start() < vid_match.start()]
            if nums_before_vid:
                seq_num = nums_before_vid[0].group(0)
            else:
                # fallback to first numeric
                seq_num = num_iter[0].group(0)
        else:
            seq_num = num_iter[0].group(0)

    # --- extract name after 'मतदाराचे पूर्ण' (robust) ---
    # allow variants and no-space after ः
    name_pattern = re.compile(
        r'(?:मतदाराचे\s*पूर्ण[:：]?\s*[:]?\s*|मतदाराचे[:：]?\s*|मतदार\s*पूर्ण[:：]?\s*)'
        r'([\u0900-\u097F\w\.\-]{1,}\s*(?:[\u0900-\u097F\w\.\-]+\s*){0,5})'
        r'(?=\s*(?:' + BOUNDARY_LABELS + r'|$))'
    )
    mname = name_pattern.search(text)
    if mname:
        name = mname.group(1).strip()
        # strip leading punctuation like ः or : if present
        name = re.sub(r'^[\s:：ः\-]+', '', name).strip()
        # remove trailing label word 'नांव' if OCR appended it
        name = re.sub(r'\s*नांव\s*$', '', name).strip()
    else:
        # fallback: longest Devanagari chunk before boundary labels
        # cut text at first boundary label to avoid picking father name etc
        boundary_pos = re.search(BOUNDARY_LABELS, text)
        left = text[:boundary_pos.start()] if boundary_pos else text
        devan = re.findall(r'[\u0900-\u097F\s]{3,}', left)
        name = max([d.strip() for d in devan], key=len) if devan else ""

    # final cleanup: ensure we didn't accidentally pick the 'वय' or other label as part
    if part and seq_num == part:
        # if the chosen seq_num equals the slash-part, clear seq_num (unlikely) 
        seq_num = ""

    return {
        "क्रमांक": seq_num,
        "मतदार ओळख क्रमांक": vid,
        "भाग क्रमांक": part,
        "मतदाराचे पूर्ण": name
    }

def process_file(img_path: str):
    raw = ocr_text(img_path)
    print("\nOCR raw text:", raw)
    extracted = extract_from_text(raw)
    print("-> Extracted:", extracted)
    return extracted

def process_folder(folder: str, out_csv="voter_list.csv"):
    files = sorted(glob.glob(str(Path(folder) / "*.*")))
    rows = []
    for f in files:
        print("Processing:", f)
        rows.append({**extract_from_text(ocr_text(f)), "source_file": Path(f).name})
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(out_csv, index=False, encoding='utf-8-sig')
        print("Saved:", out_csv)
    else:
        print("No images found in", folder)

if __name__ == "__main__":
    single = "box1.png"
    if Path(single).exists():
        process_file(single)
    else:
        if Path("boxes").exists():
            process_folder("boxes")
        else:
            print("Put box1.png near the script or a folder named 'boxes' with images.")
