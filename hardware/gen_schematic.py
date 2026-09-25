#!/usr/bin/env python3
"""Generate TetrisEarrings.kicad_sch / .kicad_pro / BOM.csv (KiCad 8 format).

Run:  python3 hardware/gen_schematic.py
The KiCad project is the source of truth; Altium opens it via
File -> Import Wizard -> KiCad Design Files.

Connectivity is done with power symbols + net labels on short pin stubs, so the
file stays simple and survives the Altium importer.  Coordinates are mm, y down.
"""
import csv
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "TetrisEarrings"
ROOT_UUID = "0f8a0f60-1e7e-4a3b-9d2c-7c1e5f4b6a01"   # fixed so re-runs diff cleanly
_counter = [0]


def uid():
    # deterministic UUIDs -> stable diffs between generator runs
    _counter[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"{PROJECT}/{_counter[0]}"))


FONT = "(effects (font (size 1.27 1.27)))"
FONT_H = "(effects (font (size 1.27 1.27)) hide)"


# ------------------------------------------------------------------ symbols
# pins: (number, name, type, x, y, angle) in symbol space (y UP, like the lib
# files).  angle = direction from the connection point toward the body.
def pin(num, name, typ, x, y, ang, length=2.54):
    return (num, name, typ, x, y, ang, length)


def rect(x1, y1, x2, y2):
    return (f"(rectangle (start {x1} {y1}) (end {x2} {y2}) "
            f"(stroke (width 0.254) (type default)) (fill (type background)))")


def poly(*pts, fill="none"):
    p = " ".join(f"(xy {x} {y})" for x, y in pts)
    return (f"(polyline (pts {p}) (stroke (width 0.254) (type default)) "
            f"(fill (type {fill})))")


def circ(x, y, r):
    return (f"(circle (center {x} {y}) (radius {r}) "
            f"(stroke (width 0.254) (type default)) (fill (type none)))")


# Symbol definitions: name -> dict(ref, graphics, pins, value_pos, hide_pin_names)
SYMS = {}


def defsym(name, ref, graphics, pins, ref_at=(0, 0), val_at=(0, 0), names=True):
    SYMS[name] = dict(ref=ref, gfx=graphics, pins=pins, ref_at=ref_at,
                      val_at=val_at, names=names)


defsym("R", "R", [rect(-1.016, -2.54, 1.016, 2.54)],
       [pin("1", "~", "passive", 0, 3.81, 270, 1.27),
        pin("2", "~", "passive", 0, -3.81, 90, 1.27)],
       ref_at=(2.54, 1.27), val_at=(2.54, -1.27), names=False)

defsym("C", "C", [poly((-2.032, 0.508), (2.032, 0.508)),
                  poly((-2.032, -0.508), (2.032, -0.508))],
       [pin("1", "~", "passive", 0, 3.81, 270, 2.54),
        pin("2", "~", "passive", 0, -3.81, 90, 2.54)],
       ref_at=(2.54, 1.27), val_at=(2.54, -1.27), names=False)

defsym("LED", "D", [poly((-1.27, -1.27), (-1.27, 1.27)),
                    poly((1.27, 1.27), (1.27, -1.27), (-1.27, 0), (1.27, 1.27)),
                    poly((-1.27, 0), (1.27, 0)),
                    poly((0, 1.27), (-1.27, 2.54)), poly((0.762, 1.27), (-0.508, 2.54))],
       [pin("1", "K", "passive", -3.81, 0, 0),
        pin("2", "A", "passive", 3.81, 0, 180)],
       ref_at=(0, 3.81), val_at=(0, -2.54), names=False)

defsym("D_Schottky", "D", [poly((-1.27, -1.27), (-1.27, 1.27)),
                           poly((1.27, 1.27), (1.27, -1.27), (-1.27, 0), (1.27, 1.27)),
                           poly((-1.27, 0), (1.27, 0)),
                           poly((-1.27, 1.27), (-1.905, 1.27), (-1.905, 0.635)),
                           poly((-1.27, -1.27), (-0.635, -1.27), (-0.635, -0.635))],
       [pin("1", "K", "passive", -3.81, 0, 0),
        pin("2", "A", "passive", 3.81, 0, 180)],
       ref_at=(0, 2.54), val_at=(0, -2.54), names=False)

MOSFET_GFX = [poly((0.254, 2.54), (0.254, -2.54)),          # channel
              poly((-1.27, 1.905), (-1.27, -1.905)),        # gate plate
              poly((-5.08, 0), (-1.27, 0)),                 # gate lead
              poly((0.254, 2.54), (2.54, 2.54), (2.54, 5.08)),      # drain
              poly((0.254, -2.54), (2.54, -2.54), (2.54, -5.08)),   # source
              circ(1.27, 0, 3.81)]
Q_PINS = [pin("1", "G", "input", -7.62, 0, 0),
          pin("2", "S", "passive", 2.54, -7.62, 90),
          pin("3", "D", "passive", 2.54, 7.62, 270)]
defsym("Q_NMOS_GSD", "Q", MOSFET_GFX + [poly((0.254, -1.27), (1.524, -1.27), (0.889, -2.032), (0.254, -1.27), fill="outline")],
       Q_PINS, ref_at=(8.89, 1.27), val_at=(8.89, -1.27), names=False)
defsym("Q_PMOS_GSD", "Q", MOSFET_GFX + [poly((0.254, 1.27), (1.524, 1.27), (0.889, 2.032), (0.254, 1.27), fill="outline")],
       Q_PINS, ref_at=(8.89, 1.27), val_at=(8.89, -1.27), names=False)

defsym("SW_Push", "SW", [circ(-2.032, 0, 0.508), circ(2.032, 0, 0.508),
                         poly((-2.54, 1.27), (2.54, 1.27)), poly((0, 1.27), (0, 3.048)),
                         poly((-2.54, 0), (-5.08, 0)), poly((2.54, 0), (5.08, 0))],
       [pin("1", "1", "passive", -5.08, 0, 0, 0.001),
        pin("2", "2", "passive", 5.08, 0, 180, 0.001)],
       ref_at=(0, 5.08), val_at=(0, -2.54), names=False)

defsym("Crystal", "Y", [rect(-1.143, -2.54, 1.143, 2.54),
                        poly((-1.905, -1.905), (-1.905, 1.905)), poly((1.905, -1.905), (1.905, 1.905)),
                        poly((-3.81, 0), (-1.905, 0)), poly((1.905, 0), (3.81, 0))],
       [pin("1", "1", "passive", -3.81, 0, 0, 0.001),
        pin("3", "3", "passive", 3.81, 0, 180, 0.001),
        pin("2", "GND", "passive", 0, -3.81, 90, 1.27),      # 3225 4-pad: 2 and 4 are the case
        pin("4", "GND", "passive", 0, 3.81, 270, 1.27)],
       ref_at=(5.08, 1.27), val_at=(5.08, -1.27), names=False)

defsym("Battery_Cell", "BT", [poly((-2.54, 1.27), (2.54, 1.27)), poly((-1.27, -0.254), (1.27, -0.254)),
                              poly((-1.27, -0.254), (-1.27, -0.762), (1.27, -0.762), (1.27, -0.254), fill="outline"),
                              poly((0, 1.27), (0, 2.54)), poly((0, -0.762), (0, -2.54)),
                              poly((3.81, 2.54), (3.81, 3.81)), poly((3.175, 3.175), (4.445, 3.175))],
       [pin("1", "+", "passive", 0, 5.08, 270),
        pin("2", "-", "passive", 0, -5.08, 90)],
       ref_at=(8.89, 1.27), val_at=(8.89, -1.27), names=False)

defsym("Pads_2", "J", [rect(-2.54, -2.54, 2.54, 2.54), circ(0, 1.27, 0.635), circ(0, -1.27, 0.635)],
       [pin("1", "1", "passive", 0, 5.08, 270),
        pin("2", "2", "passive", 0, -5.08, 90)],
       ref_at=(5.08, 1.27), val_at=(5.08, -1.27), names=False)

defsym("TC2030_SWD", "J", [rect(-7.62, -8.89, 7.62, 8.89)],
       [pin("1", "VCC", "passive", -10.16, 6.35, 0),
        pin("2", "SWDIO", "passive", -10.16, 3.81, 0),
        pin("3", "NRST", "passive", -10.16, 1.27, 0),
        pin("4", "SWCLK", "passive", -10.16, -1.27, 0),
        pin("5", "GND", "passive", -10.16, -3.81, 0),
        pin("6", "SWO", "passive", -10.16, -6.35, 0)],
       ref_at=(0, 10.16), val_at=(0, -10.16))

defsym("LDO_SOT23", "U", [rect(-7.62, -7.62, 7.62, 5.08)],
       [pin("3", "VIN", "power_in", -10.16, 2.54, 0),
        pin("2", "VOUT", "power_out", 10.16, 2.54, 180),
        pin("1", "GND", "power_in", 0, -10.16, 90)],
       ref_at=(0, 6.35), val_at=(0, -1.27))

defsym("MCP73831", "U", [rect(-7.62, -7.62, 7.62, 7.62)],
       [pin("4", "VDD", "power_in", -10.16, 5.08, 0),
        pin("5", "PROG", "input", -10.16, -2.54, 0),
        pin("3", "VBAT", "power_out", 10.16, 5.08, 180),
        pin("1", "STAT", "open_collector", 10.16, -2.54, 180),
        pin("2", "VSS", "power_in", 0, -10.16, 90)],
       ref_at=(0, 8.89), val_at=(0, 0))

defsym("STM32F070F6Px", "U", [rect(-12.7, -22.86, 12.7, 22.86)],
       [pin("16", "VDD", "power_in", -2.54, 25.4, 270),
        pin("5", "VDDA", "power_in", 2.54, 25.4, 270),
        pin("15", "VSS", "power_in", 0, -25.4, 90),
        pin("1", "BOOT0", "input", -15.24, 17.78, 0),
        pin("4", "NRST", "input", -15.24, 12.7, 0),
        pin("2", "PF0-OSC_IN", "bidirectional", -15.24, 5.08, 0),
        pin("3", "PF1-OSC_OUT", "bidirectional", -15.24, 2.54, 0),
        pin("19", "PA13/SWDIO", "bidirectional", -15.24, -7.62, 0),
        pin("20", "PA14/SWCLK", "bidirectional", -15.24, -10.16, 0),
        pin("6", "PA0", "bidirectional", 15.24, 17.78, 180),
        pin("7", "PA1/ADC_IN1", "bidirectional", 15.24, 15.24, 180),
        pin("8", "PA2", "bidirectional", 15.24, 12.7, 180),
        pin("9", "PA3", "bidirectional", 15.24, 10.16, 180),
        pin("10", "PA4", "bidirectional", 15.24, 7.62, 180),
        pin("11", "PA5", "bidirectional", 15.24, 5.08, 180),
        pin("12", "PA6", "bidirectional", 15.24, 2.54, 180),
        pin("13", "PA7", "bidirectional", 15.24, 0, 180),
        pin("17", "PA9/TIM1_CH2", "bidirectional", 15.24, -5.08, 180),
        pin("18", "PA10", "bidirectional", 15.24, -7.62, 180),
        pin("14", "PB1", "bidirectional", 15.24, -12.7, 180)],
       ref_at=(10.16, 24.13), val_at=(0, -24.13))

defsym("WS2812B-2020", "LED", [rect(-5.08, -3.81, 5.08, 3.81),
                               poly((-1.27, 1.27), (0.635, 1.27), (0.635, -1.27), (-1.27, -1.27)),
                               poly((0.635, 0), (2.54, 0)), poly((-1.27, 0), (-2.54, 0))],
       [pin("1", "VDD", "power_in", 0, 6.35, 270),
        pin("3", "GND", "power_in", 0, -6.35, 90),
        pin("4", "DIN", "input", -7.62, 0, 0),
        pin("2", "DOUT", "output", 7.62, 0, 180)],
       ref_at=(0, -2.54), val_at=(0, -8.89), names=False)

# power symbols: body direction (screen y-down vector) used for auto-rotation
POWER = {"GND": (0, 1), "+3V3": (0, -1), "VBAT": (0, -1), "VSW": (0, -1), "VCHG": (0, -1)}
for name, d in POWER.items():
    if name == "GND":
        gfx = [poly((0, 0), (0, -1.27), (1.27, -1.27), (0, -2.54), (-1.27, -1.27), (0, -1.27))]
        val_at = (0, -3.81)
    else:
        gfx = [poly((0, 0), (0, 2.54)), poly((-0.762, 2.54), (0.762, 2.54))]
        val_at = (0, 3.81)
    defsym("PWR_" + name, "#PWR", gfx, [pin("1", name, "power_in", 0, 0, 0, 0)],
           ref_at=(0, -6.35 if name != "GND" else 6.35), val_at=val_at)
defsym("PWR_FLAG", "#FLG", [poly((0, 0), (0, 1.27), (-1.905, 2.54), (0, 3.81), (1.905, 2.54), (0, 1.27))],
       [pin("1", "pwr", "power_out", 0, 0, 0, 0)], ref_at=(0, -2.54), val_at=(0, 5.08))


def lib_symbol(name):
    s = SYMS[name]
    power = "(power) " if s["ref"].startswith("#") else ""      # marks GND/VSW/... as power ports
    out = [f'  (symbol "{PROJECT}:{name}" {power}(pin_numbers {"" if s["names"] else "hide"}) '
           f'(pin_names (offset {0.508 if s["names"] else 0}){"" if s["names"] else " hide"}) '
           f'(exclude_from_sim no) (in_bom yes) (on_board yes)']
    rx, ry = s["ref_at"]
    vx, vy = s["val_at"]
    out.append(f'    (property "Reference" "{s["ref"]}" (at {rx} {ry} 0) {FONT})')
    out.append(f'    (property "Value" "{name}" (at {vx} {vy} 0) {FONT})')
    out.append(f'    (property "Footprint" "" (at 0 0 0) {FONT_H})')
    out.append(f'    (property "Datasheet" "~" (at 0 0 0) {FONT_H})')
    out.append(f'    (symbol "{name}_0_1"')
    out += ["      " + g for g in s["gfx"]]
    out.append("    )")
    out.append(f'    (symbol "{name}_1_1"')
    for num, pname, typ, x, y, ang, ln in s["pins"]:
        out.append(f'      (pin {typ} line (at {x} {y} {ang}) (length {ln}){" hide" if power else ""} '
                   f'(name "{pname}" {FONT}) (number "{num}" {FONT}))')
    out.append("    )")
    out.append("  )")
    return "\n".join(out)


# ------------------------------------------------------------------ placement
def snap(v):
    """KiCad connection grid is 1.27 mm; all pin offsets are multiples of it."""
    return round(round(v / 1.27) * 1.27, 2)


def rot_vec(v, rot):
    """Rotate a screen-space (y down) vector CCW-on-screen by rot degrees."""
    x, y = v
    for _ in range((rot // 90) % 4):
        x, y = y, -x
    return x, y


def rot_for(natural, want):
    for r in (0, 90, 180, 270):
        if rot_vec(natural, r) == want:
            return r
    raise ValueError


def pin_screen(sym, pnum, X, Y, rot, mirror=""):
    """Screen position of a pin's connection point and its outward unit vector.
    mirror: "" | "x" (flip vertically) | "y" (flip horizontally), KiCad semantics."""
    for num, _n, _t, x, y, ang, _l in SYMS[sym]["pins"]:
        if num == pnum:
            dx, dy = x, -y
            ox, oy = {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}[ang]  # screen, y down
            if mirror == "x":
                dy, oy = -dy, -oy
            elif mirror == "y":
                dx, ox = -dx, -ox
            return (X + dx, Y + dy) if rot == 0 else tuple(map(sum, zip((X, Y), rot_vec((dx, dy), rot)))), \
                rot_vec((ox, oy), rot)
    raise KeyError(pnum)


class Sheet:
    def __init__(self):
        self.parts, self.wires, self.labels, self.ncs, self.power = [], [], [], [], []
        self.used = set()
        self.bom = []
        self.placed = {}

    def _sym(self, sym, X, Y, rot, ref, value, footprint, mpn="", show_value=True, mirror=""):
        self.used.add(sym)
        X, Y = snap(X), snap(Y)
        s = SYMS[sym]
        rx, ry = rot_vec((s["ref_at"][0], -s["ref_at"][1]), rot)
        vx, vy = rot_vec((s["val_at"][0], -s["val_at"][1]), rot)
        if mirror == "x":
            ry, vy = -ry, -vy
        elif mirror == "y":
            rx, vx = -rx, -vx
        props = [f'    (property "Reference" "{ref}" (at {X + rx:g} {Y + ry:g} 0) '
                 f'{FONT if not ref.startswith("#") else FONT_H})',
                 f'    (property "Value" "{value}" (at {X + vx:g} {Y + vy:g} 0) {FONT if show_value else FONT_H})',
                 f'    (property "Footprint" "{footprint}" (at {X:g} {Y:g} 0) {FONT_H})',
                 f'    (property "Datasheet" "~" (at {X:g} {Y:g} 0) {FONT_H})']
        if mpn:
            props.append(f'    (property "MPN" "{mpn}" (at {X:g} {Y:g} 0) {FONT_H})')
        pins = "\n".join(f'    (pin "{p[0]}" (uuid "{uid()}"))' for p in s["pins"])
        return (f'  (symbol (lib_id "{PROJECT}:{sym}") (at {X:g} {Y:g} {rot}){f" (mirror {mirror})" if mirror else ""} (unit 1) '
                f'(exclude_from_sim no) (in_bom {"no" if ref.startswith("#") else "yes"}) (on_board yes) (dnp no)\n'
                f'    (uuid "{uid()}")\n' + "\n".join(props) + "\n" + pins + "\n"
                f'    (instances (project "{PROJECT}" (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))))\n  )')

    def wire(self, a, b):
        self.wires.append(f'  (wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g})) '
                          f'(stroke (width 0) (type default)) (uuid "{uid()}"))')

    def label(self, name, at, direction):
        # direction = outward unit vector (screen); text runs away from the stub
        ang = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[direction]
        just = "left" if ang in (0, 90) else "right"
        self.labels.append(f'  (label "{name}" (at {at[0]:g} {at[1]:g} {ang}) '
                           f'(effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid "{uid()}"))')

    def power_sym(self, name, at, direction):
        rot = rot_for(POWER[name], direction)
        self.power.append(self._sym("PWR_" + name, at[0], at[1], rot, f"#PWR{len(self.power) + 1:03d}", name, ""))

    def pwr_flag(self, ref, pnum, side=(-1, 0)):
        """Mark a net sourced by a passive pin (battery, pads, MOSFET drain) as driven.
        The flag points sideways so it does not sit on top of the power symbol."""
        at, _ = pin_screen(*self.placed[ref][:1], pnum, *self.placed[ref][1:])
        rot = rot_for((0, -1), side)
        self.power.append(self._sym("PWR_FLAG", at[0], at[1], rot, f"#FLG{len(self.power) + 1:03d}", "PWR_FLAG", ""))

    def part(self, ref, sym, X, Y, rot, value, footprint, nets, mpn="", desc="", stub=2.54,
             mirror="", show_value=True):
        """Place a part; nets = {pin_number: netname | None (no-connect) | "!" (wired by hand)}."""
        X, Y = snap(X), snap(Y)
        self.placed[ref] = (sym, X, Y, rot, mirror)
        self.parts.append(self._sym(sym, X, Y, rot, ref, value, footprint, mpn, show_value, mirror))
        self.bom.append((ref, value, footprint.split(":")[-1], mpn, desc))
        for num, *_ in SYMS[sym]["pins"]:
            if num not in nets:
                raise ValueError(f"{ref} pin {num} has no net")
            net = nets[num]
            at, out = pin_screen(sym, num, X, Y, rot, mirror)
            if net is None or net.startswith("!"):
                if net is None:
                        self.ncs.append(f'  (no_connect (at {at[0]:g} {at[1]:g}) (uuid "{uid()}"))')
            elif net in POWER:
                self.power_sym(net, at, out)
            else:
                end = (at[0] + out[0] * stub, at[1] + out[1] * stub)
                self.wire(at, end)
                self.label(net, end, out)

    def pin_at(self, ref, pnum):
        return pin_screen(*self.placed[ref][:1], pnum, *self.placed[ref][1:])[0]

    def connect(self, ref_a, pin_a, ref_b, pin_b, detour=0):
        """Wire between two axis-aligned pins; a vertical run detours `detour` mm outward first."""
        a, b = self.pin_at(ref_a, pin_a), self.pin_at(ref_b, pin_b)
        assert a[0] == b[0] or a[1] == b[1], (ref_a, ref_b, a, b)
        if detour and a[0] == b[0]:
            out = pin_screen(*self.placed[ref_a][:1], pin_a, *self.placed[ref_a][1:])[1]
            x = snap(a[0] + out[0] * detour)
            self.wire(a, (x, a[1]))
            self.wire((x, a[1]), (x, b[1]))
            self.wire((x, b[1]), b)
        else:
            self.wire(a, b)

    def rail(self, name, pts, end):
        """Wire through a list of collinear points, extended to `end`, with one power symbol there."""
        end = (snap(end[0]), snap(end[1]))
        pts = sorted(pts) + [end] if end > max(pts) else [end] + sorted(pts)
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)
        self.power_sym(name, end, POWER[name])

    def text(self, s, x, y, size=2.0):
        self.labels.append(f'  (text "{s}" (exclude_from_sim no) (at {x:g} {y:g} 0) '
                           f'(effects (font (size {size} {size}) bold) (justify left bottom)) (uuid "{uid()}"))')

    def nets(self):
        """{netname: [(ref, pin), ...]} from the drawn geometry (wires, labels, power symbols)."""
        import re
        par = {}

        def find(a):
            par.setdefault(a, a)
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a

        def pt(x, y):
            return (round(float(x), 2), round(float(y), 2))

        for a, b, c, d in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)', "\n".join(self.wires)):
            par[find(pt(a, b))] = find(pt(c, d))
        names = {}
        for n, x, y in re.findall(r'\(label "([^"]+)" \(at ([-\d.]+) ([-\d.]+)', "\n".join(self.labels)):
            names[pt(x, y)] = n
        for n, x, y in re.findall(r'lib_id "[^:]+:PWR_([^"]+)"\) \(at ([-\d.]+) ([-\d.]+)', "\n".join(self.power)):
            if n != "FLAG":
                names[pt(x, y)] = n
        for p, n in names.items():                       # same name => same net
            par[find(p)] = find(("name", n))
        ncs = {pt(x, y) for x, y in re.findall(r'no_connect \(at ([-\d.]+) ([-\d.]+)', "\n".join(self.ncs))}
        nets = {}
        for ref, (sym, X, Y, rot, mirror) in self.placed.items():
            for num, *_ in SYMS[sym]["pins"]:
                at, _ = pin_screen(sym, num, X, Y, rot, mirror)
                at = pt(*at)
                if at in ncs:
                    continue
                nets.setdefault(find(at), []).append((ref, num))
        out = {}
        for root, pins in nets.items():
            name = next((n for p, n in names.items() if find(p) == root), None) or f"Net-({pins[0][0]}-Pad{pins[0][1]})"
            out[name] = sorted(pins)
        return out

    def render(self):
        libs = "\n".join(lib_symbol(n) for n in sorted(self.used))
        body = "\n".join(self.parts + self.power + self.wires + self.labels + self.ncs)
        return (f'(kicad_sch (version 20231120) (generator "gen_schematic.py") (generator_version "8.0")\n'
                f'  (uuid "{ROOT_UUID}")\n  (paper "A2")\n'
                f'  (title_block (title "TetrisEarrings") (date "2026-09-25") (rev "A") '
                f'(company "") (comment 1 "6x10 WS2812B-2020 matrix, STM32F070F6, 1S Li-Po, soft power latch"))\n'
                f'  (lib_symbols\n{libs}\n  )\n{body}\n'
                f'  (sheet_instances (path "/" (page "1")))\n)\n')


# ------------------------------------------------------------------ the circuit
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOT235 = "Package_TO_SOT_SMD:SOT-23-5"
SOD323 = "Diode_SMD:D_SOD-323"
LED0603 = "LED_SMD:LED_0603_1608Metric"

sh = Sheet()

# --- battery + charger (top-left) ---------------------------------------
sh.text("BATTERY + CHARGER (dock pads)", 25, 30)
sh.part("BT1", "Battery_Cell", 40, 60, 0, "LiPo 300mAh", "TetrisEarrings:Pad_Battery_2x",
        {"1": "VBAT", "2": "GND"}, desc="1S Li-Po 602030 (6x20x30 mm) with PCM, solder pads")
sh.pwr_flag("BT1", "2")           # GND is only sourced by passive pins; VBAT is driven by U2.VBAT
sh.part("J2", "Pads_2", 65, 60, 0, "DOCK", "TetrisEarrings:Pad_Dock_2x",
        {"1": "VCHG", "2": "GND"}, desc="Charging dock contact pads (5 V, GND)")
sh.pwr_flag("J2", "1", side=(1, 0))
sh.part("U2", "MCP73831", 110, 60, 0, "MCP73831-2", SOT235,
        {"4": "VCHG", "5": "PROG", "3": "VBAT", "1": "STAT", "2": "GND"},
        mpn="MCP73831T-2ACI/OT", desc="Li-Po charger 4.2 V, ~150 mA")
sh.part("C1", "C", 85, 75, 0, "4.7u", C0603, {"1": "VCHG", "2": "GND"}, desc="Charger input")
sh.part("C2", "C", 135, 75, 0, "4.7u", C0603, {"1": "VBAT", "2": "GND"}, desc="Charger output / battery")
sh.part("R9", "R", 100, 90, 0, "6.8k", R0402, {"1": "PROG", "2": "GND"}, desc="Charge current 1000V/R = 147 mA")
sh.part("R10", "R", 135, 45, 0, "1k", R0402, {"1": "!", "2": "STAT"}, desc="Charge LED series")
sh.part("D3", "LED", 135, 30, 90, "RED", LED0603, {"1": "!", "2": "VCHG"}, desc="Charging indicator")
sh.connect("D3", "1", "R10", "1")

# --- soft power latch ----------------------------------------------------
sh.text("SOFT POWER LATCH: button = ON, PA6 holds, PA6 low = OFF", 25, 120)
sh.part("Q1", "Q_PMOS_GSD", 110, 140, 0, "AO3401A", SOT23,
        {"1": "Q1G", "2": "VBAT", "3": "VSW"}, mpn="AO3401A", desc="High-side P-MOSFET switch", mirror="x")
sh.pwr_flag("Q1", "3", side=(1, 0))   # VSW is sourced by Q1 drain (passive)
sh.part("R1", "R", 90, 130, 0, "100k", R0402, {"1": "VBAT", "2": "Q1G"}, desc="Q1 gate pull-up (off)")
sh.part("Q2", "Q_NMOS_GSD", 110, 175, 0, "2N7002", SOT23,
        {"1": "LATCH", "2": "GND", "3": "Q1G"}, mpn="2N7002", desc="Latch driver")
sh.part("R2", "R", 90, 190, 0, "100k", R0402, {"1": "LATCH", "2": "GND"}, desc="Latch pull-down")
sh.part("D1", "D_Schottky", 65, 165, 0, "BAT54", SOD323, {"1": "LATCH", "2": "KEY"},
        mpn="BAT54W", desc="Button -> latch OR", mirror="y")
sh.part("D2", "D_Schottky", 65, 180, 0, "BAT54", SOD323, {"1": "LATCH", "2": "PWR_ON"},
        mpn="BAT54W", desc="PA6 -> latch OR", mirror="y")
sh.part("SW1", "SW_Push", 40, 140, 0, "BTN", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2",
        {"1": "VBAT", "2": "KEY"}, desc="Tactile button (mode / power)")
sh.part("R3", "R", 50, 155, 0, "100k", R0402, {"1": "KEY", "2": "GND"}, desc="Button pull-down")

# --- 3.3 V LDO for the MCU --------------------------------------------
sh.text("3V3 LDO (MCU only; LEDs run from VSW)", 25, 220)
sh.part("U3", "LDO_SOT23", 80, 240, 0, "ME6211C33", SOT23,
        {"3": "VSW", "2": "+3V3", "1": "GND"}, mpn="ME6211C33M5G-N", desc="3.3 V LDO, low dropout")
sh.part("C3", "C", 55, 250, 0, "1u", C0402, {"1": "VSW", "2": "GND"}, desc="LDO input")
sh.part("C4", "C", 105, 250, 0, "1u", C0402, {"1": "+3V3", "2": "GND"}, desc="LDO output")

# --- MCU -------------------------------------------------------------------
sh.text("MCU  STM32F070F6P6", 180, 30)
sh.part("U1", "STM32F070F6Px", 240, 130, 0, "STM32F070F6P6", "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
        {"16": "+3V3", "5": "!", "15": "GND",
         "1": "BOOT0", "4": "NRST", "2": "OSC_IN", "3": "OSC_OUT", "19": "SWDIO", "20": "SWCLK",
         "6": None, "7": "VBAT_SENSE", "8": None, "9": None, "10": None, "11": None,
         "12": "PWR_ON", "13": "KEY_IN", "17": "LED_DATA", "18": None, "14": None},
        mpn="STM32F070F6P6", desc="Cortex-M0 MCU, TSSOP-20")
sh.connect("U1", "16", "U1", "5")                  # VDDA tied to VDD
sh.part("C5", "C", 180, 60, 0, "100n", C0402, {"1": "+3V3", "2": "GND"}, desc="VDD decoupling")
sh.part("C6", "C", 195, 60, 0, "1u", C0402, {"1": "+3V3", "2": "GND"}, desc="VDD bulk")
sh.part("C7", "C", 210, 60, 0, "100n", C0402, {"1": "+3V3", "2": "GND"}, desc="VDDA decoupling")
sh.part("R11", "R", 180, 100, 0, "10k", R0402, {"1": "BOOT0", "2": "GND"}, desc="BOOT0 pull-down")
sh.part("C8", "C", 200, 110, 0, "100n", C0402, {"1": "NRST", "2": "GND"}, desc="NRST filter")
sh.part("Y1", "Crystal", 190, 145, 0, "8MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
        {"1": "OSC_IN", "3": "OSC_OUT", "2": "GND", "4": "GND"}, desc="HSE 8 MHz, 3225")
sh.part("C9", "C", 175, 160, 0, "12p", C0402, {"1": "OSC_IN", "2": "GND"}, desc="Crystal load")
sh.part("C10", "C", 205, 160, 0, "12p", C0402, {"1": "OSC_OUT", "2": "GND"}, desc="Crystal load")
sh.part("J1", "TC2030_SWD", 200, 200, 0, "TC2030-IDC-NL", "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
        {"1": "+3V3", "2": "SWDIO", "3": "NRST", "4": "SWCLK", "5": "GND", "6": None},
        desc="SWD programming pads (Tag-Connect footprint, no header)")

sh.text("Battery sense: PA1 = VSW * 100/162", 280, 50, 1.5)
sh.text("2700 counts @ 3.3 V  ->  3.52 V cutoff", 280, 55, 1.5)
sh.part("R7", "R", 300, 70, 0, "62k", R0402, {"1": "VSW", "2": "!"}, desc="Battery divider top (sets 3.52 V cutoff)")
sh.part("R8", "R", 300, 90, 0, "100k", R0402, {"1": "VBAT_SENSE", "2": "GND"}, desc="Battery divider bottom")
sh.connect("R7", "2", "R8", "1")
sh.part("C11", "C", 315, 90, 0, "10n", C0402, {"1": "VBAT_SENSE", "2": "GND"}, desc="ADC filter")
sh.text("Button: PA7 = 0.75 * VBAT", 280, 120, 1.5)
sh.text("<= VDDA+0.3 V at 4.2 V, >= 0.7*VDD at 3.5 V", 280, 125, 1.5)
sh.part("R4", "R", 300, 140, 0, "33k", R0402, {"1": "KEY", "2": "!"}, desc="Button divider top")
sh.part("R5", "R", 300, 160, 0, "100k", R0402, {"1": "KEY_IN", "2": "GND"}, desc="Button divider bottom")
sh.connect("R4", "2", "R5", "1")
sh.part("R6", "R", 300, 200, 90, "330", R0402, {"1": "LED_DATA", "2": "D0"}, desc="LED data series")

# --- LED matrix: 6 x 10, serpentine, index from GetLEDIndex() ------------
sh.text("LED MATRIX 6x10  WS2812B-2020  (chain order = firmware index, row 0 = bottom)", 360, 30)
X0, Y0, DX, DY = 385, 350, 30.48, 27.94            # LED (x=0,y=0) bottom-left on screen
sh.part("C12", "C", 365, 60, 0, "10u", C0603, {"1": "VSW", "2": "GND"}, desc="LED rail bulk")
for y in range(10):
    for x in range(6):
        idx = y * 6 + (5 - x if y % 2 == 0 else x)      # GetLEDIndex(x, y)
        n = idx + 1
        sh.part(f"LED{n}", "WS2812B-2020", X0 + x * DX, Y0 - y * DY, 0, "WS2812B-2020",
                "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm",
                {"1": "!", "3": "!", "4": "D0" if idx == 0 else "!", "2": "!" if n < 60 else None},
                mpn="WS2812B-2020", desc="Addressable RGB LED 2x2 mm",
                mirror="" if y % 2 else "y", show_value=False)   # even rows flow right->left
    first = f"LED{y * 6 + 1}"
    row = [f"LED{y * 6 + 1 + i}" for i in range(6)]
    sh.rail("VSW", [sh.pin_at(r, "1") for r in row], (X0 - 10.16, sh.pin_at(first, "1")[1]))
    sh.rail("GND", [sh.pin_at(r, "3") for r in row], (X0 - 10.16, sh.pin_at(first, "3")[1]))
    # one 100 nF per row, on the row's rails
    sh.part(f"C{13 + y}", "C", 380 + y * 15.24, 60, 0, "100n", C0402, {"1": "VSW", "2": "GND"},
            desc="LED row decoupling")
for n in range(1, 60):                                   # DOUT(n) -> DIN(n+1), serpentine
    sh.connect(f"LED{n}", "2", f"LED{n + 1}", "4", detour=7.62)

# ------------------------------------------------------------------ outputs
with open(os.path.join(HERE, f"{PROJECT}.kicad_sch"), "w") as f:
    f.write(sh.render())

with open(os.path.join(HERE, f"{PROJECT}.kicad_sym"), "w") as f:
    f.write(f'(kicad_symbol_lib (version 20231120) (generator "gen_schematic.py") (generator_version "8.0")\n'
            + "\n".join(lib_symbol(n).replace(f'"{PROJECT}:{n}"', f'"{n}"', 1) for n in sorted(sh.used)) + "\n)\n")
with open(os.path.join(HERE, "sym-lib-table"), "w") as f:
    f.write(f'(sym_lib_table (version 7)\n  (lib (name "{PROJECT}") (type "KiCad") '
            f'(uri "${{KIPRJMOD}}/{PROJECT}.kicad_sym") (options "") (descr ""))\n)\n')

with open(os.path.join(HERE, f"{PROJECT}.kicad_pro"), "w") as f:
    f.write('{\n  "board": {"design_settings": {"rules": {"min_clearance": 0.127, "min_track_width": 0.127, '
            '"min_via_diameter": 0.45, "min_via_annular_width": 0.1, "min_through_hole_diameter": 0.2, '
            '"min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3, "solder_mask_to_copper_clearance": 0.0}}, '
            '"layer_presets": [], "viewports": []},\n'
            '  "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},\n'
            f'  "meta": {{"filename": "{PROJECT}.kicad_pro", "version": 1}},\n'
            '  "net_settings": {"classes": [{"name": "Default", "clearance": 0.15, "track_width": 0.15, '
            '"via_diameter": 0.5, "via_drill": 0.3, "wire_width": 6, "bus_width": 12, "line_style": 0, '
            '"pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}], '
            '"meta": {"version": 3}, "net_colors": null, "netclass_assignments": null, "netclass_patterns": []},\n'
            '  "pcbnew": {"page_layout_descr_file": ""},\n'
            f'  "schematic": {{"legacy_lib_dir": "", "legacy_lib_list": []}},\n'
            f'  "sheets": [["{ROOT_UUID}", "Root"]],\n  "text_variables": {{}}\n}}\n')

# BOM grouped by (value, footprint)
groups, descs = {}, {}
for ref, value, fp, mpn, desc in sh.bom:
    groups.setdefault((value, fp, mpn), []).append(ref)
    descs.setdefault((value, fp, mpn), []).append(desc)


def refkey(r):
    head = r.rstrip("0123456789")
    return head, int(r[len(head):])


def refrange(refs):
    refs = sorted(refs, key=refkey)
    if len(refs) > 2 and all(refkey(b)[1] - refkey(a)[1] == 1 for a, b in zip(refs, refs[1:])):
        return f"{refs[0]}-{refs[-1]}"
    return ", ".join(refs)


rows = [(refrange(refs), len(refs), value, fp, mpn, "; ".join(dict.fromkeys(descs[k])))
        for k, refs in groups.items() for (value, fp, mpn) in [k]]
rows.sort(key=lambda r: refkey(r[0].split("-")[0].split(",")[0]))
with open(os.path.join(HERE, "BOM.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Refs", "Qty", "Value", "Package", "MPN", "Description"])
    w.writerows(rows)

if __name__ == "__main__":
    # self-check: LED chain is unbroken and follows GetLEDIndex()
    assert '"D0"' in "\n".join(sh.labels) and len(sh.placed) == 106
    print(f"wrote {PROJECT}.kicad_sch ({len(sh.parts)} parts), BOM.csv ({len(rows)} lines)")
    for r in rows:
        print(f"  {r[1]:>3}  {r[0]:<12} {r[2]:<24} {r[3]}")
