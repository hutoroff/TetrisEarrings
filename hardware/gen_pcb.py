#!/usr/bin/env python3
"""Generate TetrisEarrings.kicad_pcb from the schematic generator's netlist.

Run:  python3 hardware/gen_pcb.py        (after gen_schematic.py; needs KiCad's footprint libs)

Board: 24 x 48 mm, 4 layers, 0.8 mm:  F.Cu LEDs + data chain | In1 GND plane |
In2 VSW plane | B.Cu everything else + GND pour.  LEDs at 3.5 mm pitch; odd rows are
rotated 180 deg so DOUT->DIN between neighbours is a short jog and every row gap carries
one front rail (VSW / GND alternating).  Rails hug the lower row, leaving a via band in
each gap, and reach the planes only through vias at the board edges, so the back side
stays free for parts.
Back-side signals are autorouted by route.py (Freerouting).
"""
import glob
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]]
sys.path.insert(0, HERE)
import gen_schematic as sch                   # noqa: E402  (imports regenerate the schematic too)

FP_DIRS = glob.glob("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints") + \
    glob.glob("/usr/share/kicad/footprints") + glob.glob(os.path.expanduser("~/.local/share/kicad/*/footprints"))
_counter = [0]


def uid():
    _counter[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"pcb/{_counter[0]}"))


# ------------------------------------------------------------------ board constants
W, H = 24.0, 48.0
PITCH = 3.5
LED_X = [3.25 + PITCH * c for c in range(6)]          # column centres
LED_Y = [40.0 - PITCH * r for r in range(10)]         # row centres, row 0 at the bottom
TRACK, POWER_TRACK = 0.15, 0.25
VIA, DRILL = 0.45, 0.2                                 # JLC 4-layer: 0.45/0.2 is standard, no surcharge
RAIL_W, CLR = 0.2, 0.15
PAD_EDGE = 0.55 + 0.35                                 # LED pad outer edge from LED centre (y)
GND_VIA_X, VSW_VIA_X = 1.0, 23.0                       # rail-to-plane vias in the edge strips


def rail_y(k):
    """Gap k lies between row k and row k+1 (k = -1: below row 0, k = 9: above row 9).
    The rail hugs the lower row (larger y), except the top gap which hugs row 9."""
    if k == 9:
        return LED_Y[9] - PAD_EDGE - CLR - RAIL_W / 2
    return LED_Y[k] - PAD_EDGE - CLR - RAIL_W / 2 if k >= 0 else LED_Y[0] + PAD_EDGE + CLR + RAIL_W / 2

# ------------------------------------------------------------------ footprints
CUSTOM = {
    "TetrisEarrings:Pad_Dock_2x": ('(footprint "TetrisEarrings:Pad_Dock_2x" (layer "F.Cu")\n'
                                   '  (attr smd exclude_from_pos_files exclude_from_bom)\n'
                                   '  (property "Reference" "REF**" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
                                   '  (property "Value" "VAL" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12)) hide))\n'
                                   '  (pad "1" smd rect (at -7.5 0) (size 3.5 2.2) (layers "F.Cu" "F.Mask"))\n'
                                   '  (pad "2" smd rect (at 7.5 0) (size 3.5 2.2) (layers "F.Cu" "F.Mask"))\n)'),
    "TetrisEarrings:Pad_Battery_2x": ('(footprint "TetrisEarrings:Pad_Battery_2x" (layer "F.Cu")\n'
                                      '  (attr smd exclude_from_pos_files)\n'
                                      '  (property "Reference" "REF**" (at 2.5 0 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
                                      '  (property "Value" "VAL" (at 0 3 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12)) hide))\n'
                                      '  (fp_text user "+" (at -2 -1.25 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
                                      '  (pad "1" smd rect (at 0 -1.25) (size 2.5 1.8) (layers "F.Cu" "F.Mask"))\n'
                                      '  (pad "2" smd rect (at 0 1.25) (size 2.5 1.8) (layers "F.Cu" "F.Mask"))\n)'),
}


def load_footprint(name):
    if name in CUSTOM:
        return CUSTOM[name]
    lib, fp = name.split(":")
    for d in FP_DIRS:
        path = os.path.join(d, lib + ".pretty", fp + ".kicad_mod")
        if os.path.exists(path):
            return open(path).read()
    raise FileNotFoundError(name)


NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"


def pads_of(text):
    """[(number, x, y)] in footprint-local coordinates (library orientation, front)."""
    return [(m.group(1), float(m.group(2)), float(m.group(3)))
            for m in re.finditer(rf'\(pad "([^"]*)" \w+ \w+\s*\(at ({NUM}) ({NUM})', text)]


PAD_RE = re.compile(rf'\(pad "([^"]*)" (\w+) \w+\s*\(at ({NUM}) ({NUM})(?: ({NUM}))?\)\s*\(size ({NUM}) ({NUM})\)'
                    rf'(?:\s*\(drill ({NUM})\))?')


def blocks(text, head):
    """Spans (start, end) of every balanced "(head ..." s-expression in text."""
    out, i = [], 0
    while (i := text.find("(" + head, i)) != -1:
        if text[i + 1 + len(head)] not in " \n\t)":
            i += 1
            continue
        depth, j = 0, i
        while True:
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            if text[j] == '"':                       # skip strings (may contain parens)
                j = text.index('"', j + 1)
            if depth == 0:
                break
            j += 1
        out.append((i, j + 1))
        i = j + 1
    return out


def rot_xy(x, y, rot):
    for _ in range((rot // 90) % 4):          # KiCad: +90 deg maps (x, y) -> (y, -x)
        x, y = y, -x
    return x, y


class Board:
    def __init__(self):
        self.nets = {"": 0}
        self.items, self.parts, self.pads = [], {}, {}
        self.fp_cache = {}
        self.padgeo = []        # (ref, num, layer "F"/"B"/"FB", cx, cy, half_w, half_h, net)
        self.segs = []          # (layer, a, b, width, net)
        self.vias = []          # (pos, net)

    def net(self, name):
        if name not in self.nets:
            self.nets[name] = len(self.nets)
        return self.nets[name]

    def place(self, ref, footprint, x, y, rot=0, back=False, value="", pad_nets=None):
        text = self.fp_cache.setdefault(footprint, load_footprint(footprint))
        text = re.sub(r'\((version|generator_version) \S+\)\s*', '', text)
        text = re.sub(r'\((generator|descr|tags) "(?:[^"\\]|\\.)*"\)\s*', '', text)
        text = re.sub(r'\(embedded_fonts \w+\)\s*', '', text)
        if back:
            for a, b in (("F.Cu", "B.Cu"), ("F.Paste", "B.Paste"), ("F.Mask", "B.Mask"),
                         ("F.SilkS", "B.SilkS"), ("F.Fab", "B.Fab"), ("F.CrtYd", "B.CrtYd")):
                text = text.replace(f'"{a}"', f'"{b}"')
            text = re.sub(rf'\((start|end|center|mid|xy) ({NUM}) ({NUM})\)',
                          lambda m: f'({m.group(1)} {m.group(2)} {-float(m.group(3)):g})', text)
            text = re.sub(r'\(justify ([^)]*)\)', r'(justify \1 mirror)', text)
            for a, b in reversed(blocks(text, "effects")):   # back-side text must read mirrored
                if "justify" not in text[a:b]:
                    text = text[:a] + "(effects (justify mirror)" + text[a + len("(effects"):]
        if ref.startswith("LED"):               # the front is the jewellery face: no silkscreen there
            for a, b in reversed([sp for h in ("fp_line", "fp_poly", "fp_circle", "fp_arc", "fp_rect")
                                  for sp in blocks(text, h)]):
                if '"F.SilkS"' in text[a:b]:
                    text = text[:a] + text[b:]
        # references go to the fab layer (assembly uses the CPL file); dense silk refs only overlap
        for a, b in blocks(text, 'property "Reference"'):
            text = text[:a] + text[a:b].replace('"F.SilkS"', '"F.Fab"').replace('"B.SilkS"', '"B.Fab"') + text[b:]
        sign = -1 if back else 1

        def fix_at(m):
            yy = -float(m.group(2)) if back else float(m.group(2))
            ang = (sign * float(m.group(3) or 0) + rot) % 360
            return f'(at {m.group(1)} {yy:g} {ang:g})'
        text = re.sub(rf'\(at ({NUM}) ({NUM})(?: ({NUM}))?\)', fix_at, text)
        text = re.sub(r'\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', text)
        text = re.sub(r'\(property "Value" "[^"]*"', f'(property "Value" "{value}"', text)
        if MPN.get(ref):
            _a, end = blocks(text, 'property "Value"')[0]
            text = (text[:end] + f'\n\t(property "MPN" "{MPN[ref]}" (at 0 0 0) (layer "{"B" if back else "F"}.Fab") '
                    f'(hide yes) (uuid "{uid()}") (effects (font (size 1 1) (thickness 0.15))))' + text[end:])
        pad_nets = pad_nets or {}

        def add_net(m):
            n = pad_nets.get(m.group(1))
            return m.group(0) + (f' (net {self.net(n)} "{n}")' if n else "")
        text = re.sub(r'\(pad "([^"]*)" (?:smd|connect|thru_hole) \w+', add_net, text)
        text = re.sub(r'\(footprint "[^"]*"', f'(footprint "{footprint}"\n  (at {x:g} {y:g} {rot})', text, count=1)
        text = text.rstrip()[:-1] + f'  (uuid "{uid()}")\n)'
        self.items.append(text)
        self.parts[ref] = (footprint, x, y, rot, back)
        for m in PAD_RE.finditer(self.fp_cache[footprint]):
            num, kind = m.group(1), m.group(2)
            px, py, pang = float(m.group(3)), float(m.group(4)), float(m.group(5) or 0)
            sw, sh = float(m.group(6)), float(m.group(7))
            dx, dy = rot_xy(px, -py if back else py, rot)
            cx, cy = round(x + dx, 4), round(y + dy, 4)
            if ((-pang if back else pang) + rot) % 180 == 90:
                sw, sh = sh, sw
            if kind == "np_thru_hole":
                d = float(m.group(8))
                self.padgeo.append((ref, "", "FB", cx, cy, d / 2, d / 2, None))
                continue
            self.padgeo.append((ref, num, "B" if back else "F", cx, cy, sw / 2, sh / 2, pad_nets.get(num)))
            if num:
                self.pads.setdefault(ref, {})[num] = (cx, cy)

    def pad(self, ref, num):
        return self.pads[ref][str(num)]

    def track(self, net, pts, layer, width=TRACK):
        for a, b in zip(pts, pts[1:]):
            if a == b:
                continue
            self.segs.append((layer[0], a, b, width, net))
            self.items.append(f'  (segment (start {a[0]:g} {a[1]:g}) (end {b[0]:g} {b[1]:g}) (width {width}) '
                              f'(layer "{layer}") (net {self.net(net)}) (uuid "{uid()}"))')

    def via(self, net, at):
        self.vias.append((at, net))
        self.items.append(f'  (via (at {at[0]:g} {at[1]:g}) (size {VIA}) (drill {DRILL}) (layers "F.Cu" "B.Cu") '
                          f'(net {self.net(net)}) (uuid "{uid()}"))')

    def zone(self, net, layer, pts):
        poly = " ".join(f"(xy {x:g} {y:g})" for x, y in pts)
        self.items.append(f'  (zone (net {self.net(net)}) (net_name "{net}") (layer "{layer}") (uuid "{uid()}") '
                          f'(hatch edge 0.5) (priority 0) (connect_pads (clearance 0.2)) (min_thickness 0.2) '
                          f'(filled_areas_thickness no) (fill yes (thermal_gap 0.25) (thermal_bridge_width 0.3)) '
                          f'(polygon (pts {poly})))')

    def keepout(self, x1, y1, x2, y2):
        """No tracks/vias (the autorouter ignores the board-edge clearance rule)."""
        self.items.append(f'  (zone (net 0) (net_name "") (layers "F.Cu" "B.Cu") (uuid "{uid()}") (hatch edge 0.5) '
                          f'(connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no) '
                          f'(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour allowed) '
                          f'(footprints allowed)) (fill (thermal_gap 0.5) (thermal_bridge_width 0.5)) '
                          f'(polygon (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y1:g}) (xy {x2:g} {y2:g}) (xy {x1:g} {y2:g}))))')

    def outline(self):
        r = 2.0
        L = []
        for (x1, y1, x2, y2) in ((r, 0, W - r, 0), (W, r, W, H - r), (W - r, H, r, H), (0, H - r, 0, r)):
            L.append(f'  (gr_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (uuid "{uid()}"))')
        k = r * (1 - 0.7071)
        for (sx, sy, mx, my, ex, ey) in ((0, r, k, k, r, 0), (W - r, 0, W - k, k, W, r),
                                         (W, H - r, W - k, H - k, W - r, H), (r, H, k, H - k, 0, H - r)):
            L.append(f'  (gr_arc (start {sx:g} {sy:g}) (mid {mx:.4f} {my:.4f}) (end {ex:g} {ey:g}) (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (uuid "{uid()}"))')
        L.append(f'  (gr_circle (center 12 2.2) (end 12.8 2.2) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts") (uuid "{uid()}"))')
        L.append(f'  (gr_text "TetrisEarrings" (at 17.4 1.3 0) (layer "B.SilkS") (uuid "{uid()}") (effects (font (size 0.8 0.8) (thickness 0.12)) (justify mirror)))')
        self.items += L

    def render(self):
        nets = "\n".join(f'  (net {i} "{n}")' for n, i in sorted(self.nets.items(), key=lambda kv: kv[1]))
        layers = ('  (layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal) (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive") '
                  '(34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen") '
                  '(38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments") '
                  '(44 "Edge.Cuts" user) (45 "Margin" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard") '
                  '(48 "B.Fab" user) (49 "F.Fab" user))')
        return (f'(kicad_pcb (version 20240108) (generator "gen_pcb.py") (generator_version "8.0")\n'
                f'  (general (thickness 0.8) (legacy_teardrops no))\n  (paper "A4")\n{layers}\n'
                f'  (setup (pad_to_mask_clearance 0) (allow_soldermask_bridges_in_footprints no))\n{nets}\n'
                + "\n".join(self.items) + "\n)\n")


# ------------------------------------------------------------------ netlist from the schematic
# Net names come from KiCad's own export ("/KEY", "Net-(...)", "unconnected-(...)") so that
# schematic-parity DRC and Altium's ECO see identical names.
KICAD_CLI = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
_xml = os.path.join(tempfile.mkdtemp(), "net.xml")
subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", _xml,
                os.path.join(HERE, "TetrisEarrings.kicad_sch")], check=True, capture_output=True)
PIN_NET = {(n.get("ref"), n.get("pin")): net.get("name")
           for net in ET.parse(_xml).getroot().iter("net") for n in net}
assert {k for k in PIN_NET if not PIN_NET[k].startswith("unconnected")} == \
    {(r, p) for pins in sch.sh.nets().values() for r, p in pins}, "KiCad netlist != generator netlist"
MPN = {b[0]: b[3] for b in sch.sh.bom if b[3]}
FOOTPRINT = {ref: fp for ref, _v, fp, _m, _d in [(b[0], b[1], b[2], b[3], b[4]) for b in sch.sh.bom]}
FOOTPRINT_FULL = {}
for m in re.finditer(r'\(property "Reference" "([^"]+)".*?\(property "Footprint" "([^"]*)"', "\n".join(sch.sh.parts), re.S):
    FOOTPRINT_FULL[m.group(1)] = m.group(2)
VALUE = {b[0]: b[1] for b in sch.sh.bom}

pcb = Board()
for n in ("GND", "VSW", "VBAT", "+3V3", "VCHG"):
    pcb.net(n)


def put(ref, x, y, rot=0, back=True):
    nets = {pin: net for (r, pin), net in PIN_NET.items() if r == ref}
    if ref == "Y1":                                   # 4-pad crystal: case pads 2/4 are GND in the symbol too
        pass
    pcb.place(ref, FOOTPRINT_FULL[ref], x, y, rot, back, VALUE[ref], nets)


# --- LED matrix (front) --------------------------------------------------
for r, y in enumerate(LED_Y):
    for c, x in enumerate(LED_X):
        idx = r * 6 + (5 - c if r % 2 == 0 else c)
        put(f"LED{idx + 1}", x, y, rot=180 if r % 2 else 0, back=False)

# --- back side ------------------------------------------------------------
put("U1", 12.0, 24.0)                       # MCU: pins 1-10 left (1 at the bottom), 11-20 right
put("C5", 16.6, 24.0, 90)                   # VDD decoupling next to pins 15/16
put("C6", 18.2, 24.0, 90)
put("C7", 7.4, 24.0, 90)                    # VDDA next to pin 5
put("C8", 10.6, 41.0, 90)                   # NRST filter, next to the SWD pads
put("R11", 9.8, 28.9, 90)                   # BOOT0 -> GND
put("Y1", 5.9, 27.6, 0)                     # crystal against U1 pins 2/3 (pad 1 -> PF1, pad 3 -> PF0)
put("C9", 7.2, 30.3, 0)
put("C10", 3.0, 28.0, 90)
put("R7", 6.2, 19.6, 0)                     # battery divider -> PA1 (pin 7)
put("R8", 8.6, 19.6, 0)
put("C11", 6.2, 21.6, 0)
put("R4", 16.4, 19.6, 0)                    # button divider -> PA7 (pin 13)
put("R5", 18.8, 19.6, 0)
put("R6", 16.6, 28.4, 90)                   # LED data series -> D0 via
put("J1", 12.0, 44.6, 0)                    # Tag-Connect
put("U3", 18.6, 31.0, 0)                    # LDO
put("C3", 18.6, 34.4, 90)
put("C4", 16.6, 34.2, 90)
put("Q1", 18.6, 12.6, 0)                    # latch
put("R1", 16.0, 12.6, 90)
put("Q2", 18.6, 16.4, 0)
put("R2", 16.0, 16.4, 90)
put("D1", 12.6, 15.0, 0)
put("D2", 12.6, 17.2, 0)
put("R3", 9.4, 15.0, 90)
put("SW1", 6.5, 4.4, 0)                     # button, top strip
put("BT1", 2.5, 24.25, 0)                   # battery pads, left edge
put("U2", 5.6, 41.4, 0)                     # charger, bottom-left
put("C1", 3.2, 44.4, 90)
put("C2", 8.4, 39.4, 90)
put("R9", 5.6, 38.8, 0)
put("R10", 16.0, 6.6, 0)
put("D3", 19.6, 6.6, 0)
put("C12", 21.5, 41.3, 90)                  # LED rail bulk
for k in range(10):
    put(f"C{13 + k}", 21.5, 11.8 + 2.9 * k, 90)
put("J2", 12.0, 46.3, 0, back=False)        # dock pads, front bottom

# --- LED routing (front) ---------------------------------------------------
P = 0.915                                   # pad offset from LED centre
for r, y in enumerate(LED_Y):
    for c, x in enumerate(LED_X):
        idx = r * 6 + (5 - c if r % 2 == 0 else c)
        n = idx + 1
        # power pads -> rail of the neighbouring gap (gap above row r is k = r, below is k = r - 1)
        for pin, net in (("1", "VSW"), ("3", "GND")):
            p = pcb.pad(f"LED{n}", pin)
            k = r if p[1] < y else r - 1
            pcb.track(net, [p, (p[0], rail_y(k))], "F.Cu", RAIL_W)
        # chain within the row
        if n < 60:
            dout, din = pcb.pad(f"LED{n}", 2), pcb.pad(f"LED{n + 1}", 4)
            net = PIN_NET[(f"LED{n}", "2")]
            if (r % 2 == 0 and c > 0) or (r % 2 == 1 and c < 5):
                mid = x - PITCH / 2 if r % 2 == 0 else x + PITCH / 2
                pcb.track(net, [dout, (mid, dout[1]), (mid, din[1]), din], "F.Cu")
            else:                            # row transition, detour outside the matrix
                mid = 1.5 if r % 2 == 0 else W - 1.5
                pcb.track(net, [dout, (mid, dout[1]), (mid, din[1]), din], "F.Cu")
# rails: gap k -> VSW for even k, GND for odd k (and the outer gaps -1 / 9, which only have GND pads)
x_min, x_max = LED_X[0] - P, LED_X[5] + P                  # rails end exactly on the outermost stubs
for k in range(-1, 10):
    y = rail_y(k)
    if k % 2 == 0:                          # left end is crossed by the even->odd chain transition
        pcb.track("VSW", [(x_min, y), (VSW_VIA_X, y)], "F.Cu", RAIL_W)
        pcb.via("VSW", (VSW_VIA_X, y))
    else:                                   # right end is crossed by the odd->even transition
        end = LED_X[5] - P if k == 9 else x_max                     # top gap: only top-left GND pads
        pcb.track("GND", [(GND_VIA_X, y), (end, y)], "F.Cu", RAIL_W)
        pcb.via("GND", (GND_VIA_X, y))

# dock pads (front) down to the back / GND plane
for num, net in (("1", "VCHG"), ("2", "GND")):
    p = pcb.pad("J2", num)
    v = (p[0], 44.4)
    pcb.track(net, [p, v], "F.Cu", POWER_TRACK)
    pcb.via(net, v)

# --- plane fanout: every back-side GND / VSW pad gets its own via ------------
def _rect_dist(px, py, cx, cy, hw, hh):
    return math.hypot(max(abs(px - cx) - hw, 0), max(abs(py - cy) - hh, 0))


def _seg_dist(p, a, b):
    ax, ay, bx, by = *a, *b
    L2 = (bx - ax) ** 2 + (by - ay) ** 2
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / L2))
    return math.hypot(p[0] - ax - t * (bx - ax), p[1] - ay - t * (by - ay))


def via_ok(v, net):
    r = VIA / 2
    if not (0.3 + r <= v[0] <= W - 0.3 - r and 0.3 + r <= v[1] <= H - 0.3 - r):
        return False
    if math.hypot(v[0] - 12, v[1] - 2.2) < 0.8 + r + 0.3:           # earring hook hole
        return False
    for _ref, _n, layer, cx, cy, hw, hh, pnet in pcb.padgeo:
        need = r + (0.25 if layer == "FB" else CLR)
        if _rect_dist(*v, cx, cy, hw, hh) < need:
            return False
    for _layer, a, b, w, snet in pcb.segs:
        if snet != net and _seg_dist(v, a, b) < w / 2 + r + CLR:
            return False
    return all(math.hypot(v[0] - q[0], v[1] - q[1]) >= VIA + CLR for q, _n in pcb.vias)


def stub_ok(a, b, ref, num, net, w=POWER_TRACK):
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.02))
    pts = [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
    for pref, pnum, layer, cx, cy, hw, hh, pnet in pcb.padgeo:
        if "B" not in layer or pnet == net and (pref, pnum) == (ref, num):
            continue
        if pnet == net and pnet is not None:
            continue                                                 # touching a same-net pad is fine
        if min(_rect_dist(*q, cx, cy, hw, hh) for q in pts) < w / 2 + CLR:
            return False
    for layer, s0, s1, sw, snet in pcb.segs:
        if layer == "B" and snet != net and min(_seg_dist(q, s0, s1) for q in pts) < (sw + w) / 2 + CLR:
            return False
    return True


fanout_fail = []
for ref, num, layer, cx, cy, hw, hh, net in list(pcb.padgeo):
    if layer != "B" or net not in ("GND", "VSW"):
        continue
    for rr in [0.55 + 0.1 * i for i in range(30)]:
        found = None
        for k in range(24):
            ang = math.radians(15 * k)
            v = (round(cx + rr * math.cos(ang), 3), round(cy + rr * math.sin(ang), 3))
            if via_ok(v, net) and stub_ok((cx, cy), v, ref, num, net):
                found = v
                break
        if found:
            pcb.track(net, [(cx, cy), found], "B.Cu", POWER_TRACK)
            pcb.via(net, found)
            break
    else:
        fanout_fail.append(f"{ref}.{num}")

E = 0.35                                    # edge keepout: 0.3 mm rule + margin
for x1, y1, x2, y2 in ((0, 0, W, E), (0, H - E, W, H), (0, 0, E, H), (W - E, 0, W, H),
                       (0, 0, 2, 2), (W - 2, 0, W, 2), (0, H - 2, 2, H), (W - 2, H - 2, W, H),
                       (10.8, 1.0, 13.2, 3.4)):                       # earring hook hole
    pcb.keepout(x1, y1, x2, y2)

pcb.zone("GND", "In1.Cu", [(0, 0), (W, 0), (W, H), (0, H)])
pcb.zone("VSW", "In2.Cu", [(0, 0), (W, 0), (W, H), (0, H)])
pcb.outline()

if __name__ == "__main__":
    with open(os.path.join(HERE, "TetrisEarrings.kicad_pcb"), "w") as f:
        f.write(pcb.render())
    # project footprint libraries: KiCad's stock libs + the two pad footprints defined above
    os.makedirs(os.path.join(HERE, "TetrisEarrings.pretty"), exist_ok=True)
    for name, text in CUSTOM.items():
        with open(os.path.join(HERE, "TetrisEarrings.pretty", name.split(":")[1] + ".kicad_mod"), "w") as f:
            f.write(text.replace(f'(footprint "{name}"', f'(footprint "{name.split(":")[1]}"', 1) + "\n")
    libs = sorted({fp.split(":")[0] for fp, *_ in pcb.parts.values()} - {"TetrisEarrings"})
    with open(os.path.join(HERE, "fp-lib-table"), "w") as f:
        f.write("(fp_lib_table\n  (version 7)\n"
                '  (lib (name "TetrisEarrings") (type "KiCad") (uri "${KIPRJMOD}/TetrisEarrings.pretty") (options "") (descr ""))\n'
                + "".join(f'  (lib (name "{l}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{l}.pretty") (options "") (descr ""))\n'
                          for l in libs) + ")\n")
    print(f"wrote TetrisEarrings.kicad_pcb: {len(pcb.parts)} footprints, {len(pcb.nets) - 1} nets, "
          f"{len(pcb.vias)} vias; fanout failed: {fanout_fail or 'none'}")
    if "--pads" in os.environ.get("GEN_PCB_OPTS", ""):
        for ref in sorted(pcb.pads, key=lambda r: (r.rstrip("0123456789"), int(r.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")))):
            if ref.startswith("LED"):
                continue
            print(ref, {n: (p, PIN_NET.get((ref, n), "-")) for n, p in pcb.pads[ref].items()})
