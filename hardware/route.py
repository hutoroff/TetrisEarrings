#!/usr/bin/env python3
"""Autoroute TetrisEarrings.kicad_pcb in place with Freerouting.

Run with KiCad's bundled Python (it provides the `pcbnew` module):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/route.py

Needs Java 17+ and the Freerouting 1.9.0 jar (FREEROUTING_JAR, default ~/.cache/freerouting/fr-1.9.0.jar,
from github.com/freerouting/freerouting/releases).  1.9.0 opens a small window while it routes; 2.x
ignores the pass limit (-mp) in headless mode and never writes its session file.
gen_pcb.py places parts and draws the fixed front copper; this adds the back-side routing.
"""
import os
import subprocess
import sys
import tempfile
import time

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "TetrisEarrings.kicad_pcb")
JAR = os.environ.get("FREEROUTING_JAR", os.path.expanduser("~/.cache/freerouting/fr-1.9.0.jar"))
PASSES = int(os.environ.get("ROUTE_PASSES", "40"))
TIMEOUT = int(os.environ.get("ROUTE_TIMEOUT", "900"))      # s, safety net

tmp = tempfile.mkdtemp(prefix="route-")
dsn, ses, log = (os.path.join(tmp, n) for n in ("board.dsn", "board.ses", "freerouting.log"))

board = pcbnew.LoadBoard(BOARD)
if not pcbnew.ExportSpecctraDSN(board, dsn):
    sys.exit("DSN export failed")

cmd = ["java", "-Xmx4g", "-jar", JAR, "-de", dsn, "-do", ses, "-mp", str(PASSES), "-mt", "1"]
with open(log, "w") as f:
    proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    t0 = time.time()
    while proc.poll() is None and time.time() - t0 < TIMEOUT:
        time.sleep(2)
        if os.path.exists(ses) and os.path.getsize(ses) and time.time() - os.path.getmtime(ses) > 3:
            break                                            # 1.9.0 keeps its window open after saving
    if proc.poll() is None:
        proc.terminate()
        proc.wait()

print("freerouting log:", log)
if not os.path.exists(ses):
    sys.exit("Freerouting wrote no session file (timed out before finishing?)")

if not pcbnew.ImportSpecctraSES(board, ses):
    sys.exit("SES import failed")
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
board.Save(BOARD)
print("routed ->", BOARD)
