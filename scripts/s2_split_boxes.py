import cv2
from pathlib import Path

root = Path(__file__).parent
matches = list(root.rglob("voter_1.png"))
if not matches:
    raise FileNotFoundError("❌ Could not find 'voter_1.png'")
src = matches[0]
print(f"✅ Found image at: {src}")

out_dir = Path("voter_list_box")  # output folder
out_dir.mkdir(exist_ok=True)

img = cv2.imread(str(src))
if img is None:
    raise FileNotFoundError(f"Couldn't open {src}")

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# --- set how many rows and columns of boxes there are ---
rows, cols = 10, 3     # adjust if needed
box_h, box_w = h // rows, w // cols

index = 1
for r in range(rows):
    for c in range(cols):
        y1, y2 = r * box_h, (r + 1) * box_h
        x1, x2 = c * box_w, (c + 1) * box_w
        crop = img[y1:y2, x1:x2]
        cv2.imwrite(str(out_dir / f"voter_{index}.png"), crop)
        index += 1

print(f"✅ Saved {index-1} voter boxes to '{out_dir}'")
