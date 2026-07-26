"""copy_assets.py -- Helper script to copy generated images into data/assets/"""
import os
import shutil
import glob

BRAIN_DIR = r"C:\Users\DELL\.gemini\antigravity-ide\brain\195bb553-cefe-4546-818f-74893e7f3af0"
DEST_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "assets"))

os.makedirs(DEST_DIR, exist_ok=True)

mapping = {
    "fixer_hideout": "fixer_hideout.png",
    "steward_sanctuary": "steward_sanctuary.png",
    "vice_lounge": "vice_lounge.png",
    "offgrid_wilderness": "offgrid_wilderness.png",
    "overdose_collapse": "overdose_collapse.png"
}

for prefix, target_name in mapping.items():
    pattern = os.path.join(BRAIN_DIR, f"{prefix}_*.png")
    matches = glob.glob(pattern)
    if matches:
        latest = max(matches, key=os.path.getmtime)
        dest_path = os.path.join(DEST_DIR, target_name)
        shutil.copy2(latest, dest_path)
        print(f"Copied {os.path.basename(latest)} -> {dest_path}")
    else:
        print(f"No match for {prefix}")
