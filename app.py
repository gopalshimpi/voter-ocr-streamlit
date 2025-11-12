import streamlit as st
import subprocess
from pathlib import Path
import shutil
import time
import os

st.set_page_config(page_title="🗳️ Voter List OCR → CSV", layout="centered")
st.title("🗳️ Voter List OCR to CSV Converter")
st.markdown(
    """
Upload your voter list **PDF**, and this tool will:
1. Convert it to an image  
2. Split it into individual voter boxes  
3. Extract voter details using OCR  
4. Generate a downloadable CSV file  
"""
)

# === Helper: Clean old non-result data ===
def clean_temp_folders():
    """Delete working folders but keep result_* history."""
    folders_to_delete = ["uploads", "voter_pages", "voter_list_box"]
    for folder in folders_to_delete:
        p = Path(folder)
        if p.exists():
            shutil.rmtree(p)
            st.write(f"🧹 Removed old folder: `{p}`")
    st.info("✅ Cleaned temporary folders (kept all result_* folders).")


# === Step 1: Upload PDF ===
uploaded_pdf = st.file_uploader("📤 Upload your Voter List PDF", type=["pdf"])

if uploaded_pdf:
    # Clean up old temporary folders before new upload
    clean_temp_folders()

    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    pdf_path = uploads_dir / uploaded_pdf.name
    with open(pdf_path, "wb") as f:
        f.write(uploaded_pdf.read())

    st.success(f"✅ Uploaded: {uploaded_pdf.name}")

    # === Step 2: Start Processing ===
    if st.button("🚀 Start Processing"):
        st.info("⏳ Processing started. Please wait while the system extracts voter boxes and voter details...")

        start_time = time.time()

        # Create progress section
        progress_text = st.empty()
        progress_bar = st.progress(0)

        try:
            # Step 1 - Convert PDF → Image
            progress_text.text("🖼️ Step 1/3: Converting PDF → Image...")
            subprocess.run(["python", "scripts/s1_pdf_to_images.py"], check=True)
            progress_bar.progress(33)

            # Step 2 - Split image → voter boxes
            progress_text.text("📦 Step 2/3: Splitting page into voter boxes...")
            subprocess.run(["python", "scripts/s2_split_boxes.py"], check=True)
            progress_bar.progress(66)

            # Step 3 - OCR Extraction → CSV
            progress_text.text("🧠 Step 3/3: Extracting voter details using OCR...")
            subprocess.run(["python", "scripts/s3_generate_csv.py"], check=True)
            progress_bar.progress(100)

            elapsed = time.time() - start_time
            st.success(f"✅ All steps completed successfully in {elapsed:.1f} seconds!")

            # Step 4 - Find latest CSV
            results = sorted(
                Path(".").glob("result_*/**/*.csv"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if results:
                csv_path = results[0]
                download_name = csv_path.stem + ".csv"
                st.download_button(
                    label="⬇️ Download CSV Result",
                    data=csv_path.read_bytes(),
                    file_name=download_name,
                    mime="text/csv",
                )
                st.info(f"📁 CSV saved in folder: `{csv_path.parent.name}`")
            else:
                st.error("⚠️ Could not find output CSV file. Check logs below.")

        except subprocess.CalledProcessError as e:
            st.error(f"❌ Error while running one of the scripts: {e}")
        except Exception as e:
            st.error(f"⚠️ Unexpected error: {e}")
