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

# Step 1: Upload PDF
uploaded_pdf = st.file_uploader("📤 Upload your Voter List PDF", type=["pdf"])

if uploaded_pdf:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    pdf_path = uploads_dir / uploaded_pdf.name
    with open(pdf_path, "wb") as f:
        f.write(uploaded_pdf.read())

    st.success(f"✅ Uploaded: {uploaded_pdf.name}")

    # Step 2: Start Processing
    if st.button("🚀 Start Processing"):
        st.info(
            "⏳ Processing started. Please wait while the system extracts voter boxes and voter details..."
        )

        start_time = time.time()

        try:
            # Clean up old runs
            for folder in ["voter_pages", "voter_list_box"]:
                if Path(folder).exists():
                    shutil.rmtree(folder)

            # Step 1 - Convert PDF → Image
            st.write("🖼️ Converting PDF page to image...")
            subprocess.run(["python", "scripts/s1_pdf_to_images.py"], check=True)

            # Step 2 - Split image → voter boxes
            st.write("📦 Splitting page into voter boxes...")
            subprocess.run(["python", "scripts/s2_split_boxes.py"], check=True)

            # Step 3 - OCR Extraction → CSV
            st.write("🧠 Extracting voter details with OCR...")
            subprocess.run(["python", "scripts/s3_generate_csv.py"], check=True)

            elapsed = time.time() - start_time
            st.success(f"✅ Completed successfully in {elapsed:.1f} seconds!")

            # Step 4 - Find Result
            results = sorted(
                Path(".").glob("result_*/voter_list_output.csv"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if results:
                csv_path = results[0]
                st.download_button(
                    label="⬇️ Download CSV Result",
                    data=csv_path.read_bytes(),
                    file_name="voter_list_output.csv",
                    mime="text/csv",
                )
                st.info(f"📄 Result saved in folder: `{csv_path.parent.name}`")
            else:
                st.error("⚠️ Could not find output CSV file. Check logs below.")

        except subprocess.CalledProcessError as e:
            st.error(f"❌ Error while running one of the scripts: {e}")
        except Exception as e:
            st.error(f"⚠️ Unexpected error: {e}")
