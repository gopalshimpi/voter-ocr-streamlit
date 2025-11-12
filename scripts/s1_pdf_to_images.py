# import fitz  # PyMuPDF
# import cv2
# import numpy as np
# from pathlib import Path

# PDF_FILE = "FinalList_Ward_15-pages-9-2.pdf"
# OUT_DIR = Path("voter_pages")
# OUT_DIR.mkdir(exist_ok=True)

# # Convert PDF page to image
# doc = fitz.open(PDF_FILE)
# page = doc.load_page(0)  # first page
# pix = page.get_pixmap(dpi=300)
# img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
# img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

# # Convert to grayscale and detect boxes
# gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# blur = cv2.GaussianBlur(gray, (5, 5), 0)
# edges = cv2.Canny(blur, 50, 150)

# # Find contours (rectangular boxes)
# contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# # Sort top-to-bottom
# contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[1])

# index = 1
# for c in contours:
#     x, y, w, h = cv2.boundingRect(c)
#     if w > 400 and h > 150:  # filter likely voter boxes
#         crop = img[y:y+h, x:x+w]
#         cv2.imwrite(str(OUT_DIR / f"voter_{index}.png"), crop)
#         index += 1

# print(f"✅ Saved {index-1} voter boxes in '{OUT_DIR}' folder.")


import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
import sys

# --- PDF File Handling ---
uploads_dir = Path("uploads")
if not uploads_dir.exists():
    print("❌ uploads folder not found.")
    sys.exit(1)

# Find latest uploaded PDF
pdf_files = sorted(uploads_dir.glob("*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
if not pdf_files:
    print("❌ No PDF file found in uploads folder.")
    sys.exit(1)

PDF_FILE = pdf_files[-1]  # latest uploaded PDF
print(f"✅ Using PDF: {PDF_FILE}")

OUT_DIR = Path("voter_pages")
OUT_DIR.mkdir(exist_ok=True)

# --- Convert PDF to Image ---
doc = fitz.open(PDF_FILE)
page = doc.load_page(0)  # first page only for now
pix = page.get_pixmap(dpi=300)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

cv2.imwrite(str(OUT_DIR / "voter_1.png"), img)
print(f"✅ Saved 1 voter boxes in '{OUT_DIR}' folder.")
