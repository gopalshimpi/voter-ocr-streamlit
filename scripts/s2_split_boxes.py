import cv2
from pathlib import Path
import sys
import time

# === Folder setup ===
root = Path(__file__).parent.parent
input_dir = root / "voter_pages"
out_dir = root / "voter_list_box"

# === Wait for folder and image ===
max_wait = 20  # seconds
waited = 0

while waited < max_wait:
    if input_dir.exists():
        matches = list(input_dir.glob("*.png"))
        if matches:
            break
    print(f"⏳ Waiting for 'voter_pages' folder or image... ({waited}s)")
    time.sleep(1)
    waited += 1

# === Validate input folder ===
if not input_dir.exists():
    print("❌ Folder 'voter_pages' not found. Run s1_pdf_to_images.py first.")
    sys.exit(1)

matches = list(input_dir.glob("*.png"))
if not matches:
    print("❌ No PNG files found in 'voter_pages' even after waiting.")
    sys.exit(1)

# === Pick the first image (voter_1.png) ===
src = matches[0]
print(f"✅ Found image at: {src}")

# === Prepare output folder ===
out_dir.mkdir(exist_ok=True)

# === Read image ===
img = cv2.imread(str(src))
if img is None:
    print(f"❌ Could not open image: {src}")
    sys.exit(1)

h, w = img.shape[:2]
print(f"🖼️ Image size: {w}x{h}")

# --- Your exact cropping logic (unchanged) ---
rows, cols = 10, 3  # adjust if needed
box_h, box_w = h // rows, w // cols

index = 1
for r in range(rows):
    for c in range(cols):
        y1, y2 = r * box_h, (r + 1) * box_h
        x1, x2 = c * box_w, (c + 1) * box_w
        crop = img[y1:y2, x1:x2]
        cv2.imwrite(str(out_dir / f"voter_{index}.png"), crop)
        index += 1

print(f"✅ Saved {index - 1} voter boxes to '{out_dir}'")
