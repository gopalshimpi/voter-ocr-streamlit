import subprocess
import sys
from pathlib import Path

def run_script_live(script_name, check_dir=None, expect_ext="png"):
    print(f"\n🚀 Running {script_name} ...")
    process = subprocess.Popen(
        ["python", script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    # Stream output line-by-line as it runs
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    process.wait()
    if process.returncode != 0:
        print(f"❌ {script_name} failed.")
        sys.exit(1)

    if check_dir:
        folder = Path(check_dir)
        files = list(folder.glob(f"*.{expect_ext}"))
        if not files:
            print(f"❌ No {expect_ext.upper()} files found in {check_dir}.")
            sys.exit(1)
        print(f"✅ {len(files)} files ready in {check_dir}")

scripts = [
    ("s1_pdf_to_images.py", "voter_pages", "png"),
    ("s2_split_boxes.py", "voter_list_box", "png"),
    ("s3_generate_csv.py", None, None),
]

for name, check_dir, ext in scripts:
    run_script_live(name, check_dir, ext)

print("\n🎯 All steps finished successfully!")
