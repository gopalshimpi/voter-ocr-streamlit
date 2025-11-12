import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
import sys

# --- Allow Streamlit to pass uploaded path as argument ---
if len(sys.argv) > 1:
    PDF_FILE = sys.argv[1]
else:
    PDF_FILE = "uploads/FinalList_Ward_15-pages-9-1.pdf"  # fallback for local test

pdf_path = Path(PDF_FILE)
if not pdf_path.exists():
    print(f"❌ PDF file not found: {pdf_path}")
    sys.exit(1)

OUT_DIR = Path("voter_pages")
OUT_DIR.mkdir(exist_ok=True)

print(f"📄 Converting PDF page to image: {pdf_path.name}")

# --- Convert first page to image ---
try:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    img_path = OUT_DIR / "voter_1.png"
    cv2.imwrite(str(img_path), img)
    print(f"✅ Saved 1 voter page to '{OUT_DIR}'")
except Exception as e:
    print(f"❌ Error converting PDF: {e}")
    sys.exit(1)
