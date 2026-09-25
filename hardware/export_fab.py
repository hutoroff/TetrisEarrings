#!/usr/bin/env python3
"""Export JLCPCB fabrication + assembly files into hardware/fab/ (needs kicad-cli).

  fab/TetrisEarrings-gerbers.zip   4-layer Gerbers + Excellon drill (upload for the bare PCB)
  fab/TetrisEarrings-bom.csv       JLC BOM: Comment, Designator, Footprint, LCSC Part #
  fab/TetrisEarrings-cpl.csv       JLC pick-and-place: Designator, Mid X, Mid Y, Layer, Rotation

LCSC part numbers are left blank on purpose: JLC's BOM matcher fills them from the MPN/value,
and stock changes daily, so pick them in the order page rather than trusting a hard-coded list.
"""
import csv
import glob
import os
import shutil
import subprocess
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "TetrisEarrings.kicad_pcb")
OUT = os.path.join(HERE, "fab")
CLI = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"


def run(*args):
    subprocess.run([CLI, *args], check=True, capture_output=True)


os.makedirs(OUT, exist_ok=True)
tmp = tempfile.mkdtemp()
run("pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask", "--no-x2", "-o", tmp + "/", PCB)
run("pcb", "export", "drill", "--format", "excellon", "--drill-origin", "absolute", "--excellon-units", "mm",
    "--excellon-separate-th", "-o", tmp + "/", PCB)
with zipfile.ZipFile(os.path.join(OUT, "TetrisEarrings-gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(os.path.join(tmp, "*"))):
        z.write(f, os.path.basename(f))

pos = os.path.join(tmp, "pos.csv")
run("pcb", "export", "pos", "--side", "both", "--format", "csv", "--units", "mm", "--exclude-dnp",
    "--use-drill-file-origin", "-o", pos, PCB)
rows = list(csv.DictReader(open(pos)))
with open(os.path.join(OUT, "TetrisEarrings-cpl.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm", "Top" if r["Side"] == "top" else "Bottom", r["Rot"]])

# BOM grouped by value + footprint, only parts that are placed (the pos file already drops pads-only parts)
groups = {}
for r in rows:
    groups.setdefault((r["Val"], r["Package"]), []).append(r["Ref"])
with open(os.path.join(OUT, "TetrisEarrings-bom.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, pkg), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        w.writerow([val, ",".join(refs), pkg, ""])

print(f"wrote {OUT}: gerbers zip, BOM ({len(groups)} lines), CPL ({len(rows)} parts)")
