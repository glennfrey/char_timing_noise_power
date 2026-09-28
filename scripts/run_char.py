#!/usr/bin/env python3
"""
run_char.py — open-source std-cell characterization driver.
Mirrors the flow taught in VSD 'Library Characterization & Modelling' (GUNA-based),
reimplemented with ngspice + Python:

  1. TIMING   : tpLH/tpHL/trise/tfall across a slew x load matrix  -> Liberty tables
  2. POWER    : leakage (input pinned 0/1, DC) + dynamic (avg current @ toggle)
  3. NOISE    : crosstalk glitch peak on a victim route + crosstalk delta delay
  4. MODELING : writes Liberty (.lib) with table_lookup timing/power
  5. QA       : monotonicity + range checks on the generated tables

Usage:  python3 scripts/run_char.py          (requires ngspice on PATH)
"""
import re, subprocess, sys, itertools, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "output"
VDD  = 1.8
TEMP = 25
PROCESS = "tt"

# ---- characterization plan: the slew x load index tables -------------------
INPUT_SLEWS = [50e-12, 100e-12, 200e-12, 400e-12, 800e-12]   # input transition (s)
LOADS       = [1e-15, 5e-15, 10e-15, 25e-15, 50e-15]        # output load (F)

def ngspice(deck_text):
    tmp = OUT / "_tmp.sp"
    tmp.write_text(deck_text)
    try:
        r = subprocess.run(["ngspice", "-b", str(tmp)],
                           capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit(
            "ngspice not found on PATH.\n"
            "Install it first, e.g.:\n"
            "  macOS:   brew install ngspice\n"
            "  Ubuntu:  sudo apt install ngspice\n"
            "Then re-run: make char")
    if r.returncode != 0:
        sys.exit(f"ngspice failed on deck:\n{r.stdout}\n{r.stderr}")
    return r.stdout

def meas(stdout, name):
    # tolerate leading whitespace; distinguish "missing" from "evaluated to FAILED"
    m = re.search(rf"^\s*{name}\s*=\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", stdout, re.M | re.I)
    if m:
        return float(m.group(1))
    fail = re.search(rf"^\s*{name}\s*=\s*FAILED", stdout, re.M | re.I)
    tail = "\n".join(stdout.strip().splitlines()[-25:])
    if fail:
        sys.exit(
            f"measurement {name} evaluated to FAILED (crossing never occurred).\n"
            f"Last lines of ngspice output:\n{tail}\n"
            f"Reproduce manually: ngspice -b output/_tmp.sp")
    sys.exit(
        f"measurement {name} not found in ngspice output.\n"
        f"Last lines of ngspice output:\n{tail}\n"
        f"Reproduce manually: ngspice -b output/_tmp.sp")

def op_current(stdout):
    """Parse 'vdd#branch = <i>' from the DC operating-point printout."""
    m = re.search(r"vdd#branch\s+(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", stdout, re.I)
    if not m:
        sys.exit("operating-point current (vdd#branch) not found in ngspice output")
    return abs(float(m.group(1)))

def fmt(x):
    return f"{x:.4g}"

# ---- 1+2. TIMING & POWER sweep --------------------------------------------
def characterize():
    res = {"tpLH": [], "tpHL": [], "trise": [], "tfall": [],
           "rise_power": [], "fall_power": []}
    ileak = 0.0
    for trf, cl in itertools.product(INPUT_SLEWS, LOADS):
        out = ngspice((ROOT/"decks/tb_delay.sp").read_text()
                      .format(ROOT=ROOT, TRF=trf, CL=cl))
        res["tpLH"].append(meas(out, "tpLH"))
        res["tpHL"].append(meas(out, "tpHL"))
        res["trise"].append(meas(out, "trise"))
        res["tfall"].append(meas(out, "tfall"))

        ileak = max(op_current(ngspice((ROOT/"decks/tb_leak.sp").read_text()
                                .format(ROOT=ROOT, CL=cl, INB=0.0))),
                    op_current(ngspice((ROOT/"decks/tb_leak.sp").read_text()
                                .format(ROOT=ROOT, CL=cl, INB=VDD))))
        iavg  = abs(meas(ngspice((ROOT/"decks/tb_dyn.sp").read_text()
                         .format(ROOT=ROOT, CL=cl)), "iavg"))
        p_dyn = max(VDD * (iavg - ileak), 0.0)
        res["rise_power"].append(p_dyn / 2)
        res["fall_power"].append(p_dyn / 2)
        print(f"  slew={trf*1e12:5.0f}ps load={cl*1e15:4.1f}f  "
              f"tpLH={res['tpLH'][-1]*1e12:6.2f}ps  Pdyn={p_dyn*1e6:6.2f}uW")

    res["leakage"] = VDD * ileak
    return res

# ---- 3. NOISE ---------------------------------------------------------------
def characterize_noise():
    n = {}
    out = ngspice((ROOT/"decks/tb_noise.sp").read_text()
                  .format(ROOT=ROOT, CC=10e-15, TRF=100e-12, CL=10e-15))
    n["glitch_vout"]  = meas(out, "glitch_vpp")
    n["glitch_route"] = meas(out, "glitch_route")
    d0 = meas(ngspice((ROOT/"decks/tb_delta.sp").read_text()
              .format(ROOT=ROOT, TRF=100e-12, CL=10e-15, CC=50e-15, VA=1.8)), "tpLH")
    d1 = meas(ngspice((ROOT/"decks/tb_delta.sp").read_text()
              .format(ROOT=ROOT, TRF=100e-12, CL=10e-15, CC=50e-15, VA=0.0)), "tpLH")
    n["delta_delay"] = d1 - d0
    return n

# ---- 4. MODELING : write Liberty --------------------------------------------
def liberty_table(vals, indent="          "):
    """One values table: each slew row on its own continuation line."""
    n = len(LOADS)
    lines = []
    for i in range(len(INPUT_SLEWS)):
        row = " ".join(fmt(vals[i*n + j]) for j in range(n))
        lines.append(indent + row + " \\")
    return "\n".join(lines)

def write_lib(res):
    lib = OUT / f"inv_{PROCESS}_{VDD}v_{TEMP}c.lib"
    slew_hdr = ", ".join(fmt(s*1e9) for s in INPUT_SLEWS)
    load_hdr = ", ".join(fmt(l*1e12) for l in LOADS)

    def tbl_group(name, key):
        return (
            f"        {name} (delay_template_5x5) {{\n"
            f'          index_1 ("{slew_hdr}");\n'
            f'          index_2 ("{load_hdr}");\n'
            f"          values ( \\\n{liberty_table(res[key])}\n"
            f"          );\n"
            f"        }}"
        )

    txt = f"""/* Auto-generated by run_char.py — educational inverter characterization
 * PVT: {PROCESS.upper()} / {VDD}V / {TEMP}C. Units: ns, pF, uW. */
library (inv_char_{PROCESS}) {{
  delay_model : table_lookup;
  in_place_swap_mode : match_footprint;
  time_unit : "1ns";
  voltage_unit : "1V";
  current_unit : "1mA";
  pulling_resistance_unit : "1kohm";
  leakage_power_unit : "1uW";
  capacitive_load_unit (0.0001, "1pF");
  nom_process : 1;
  nom_voltage : {VDD};
  nom_temperature : {TEMP};

  lu_table_template (delay_template_5x5) {{
    variable_1 : input_net_transition;
    variable_2 : total_output_net_capacitance;
    index_1 ("{slew_hdr}");
    index_2 ("{load_hdr}");
  }}

  cell (inv) {{
    area : 0.1026;
    leakage_power () {{ value : {fmt(res["leakage"]*1e6)} ; }}
    pin (A) {{
      direction : input;
      capacitance : 0.0012;
    }}
    pin (Y) {{
      direction : output;
      function : "!A";
      related_ground_pin : VSS;
      related_power_pin : VDD;
      timing () {{
        related_pin : "A";
        timing_sense : negative_unate;
{tbl_group("cell_rise", "tpLH")}
{tbl_group("cell_fall", "tpHL")}
{tbl_group("rise_transition", "trise")}
{tbl_group("fall_transition", "tfall")}
      }}
      internal_power () {{
        related_pin : "A";
{tbl_group("rise_power", "rise_power")}
{tbl_group("fall_power", "fall_power")}
      }}
    }}
    pg_pin (VDD) {{ pg_type : primary_power; voltage_name : "VDD"; }}
    pg_pin (VSS) {{ pg_type : primary_ground; voltage_name : "VSS"; }}
  }}
}}
"""
    lib.write_text(txt)
    return lib

# ---- 5. QA -------------------------------------------------------------------
def qa(res):
    problems = []
    n = len(LOADS)
    for key in ["tpLH", "tpHL", "trise", "tfall"]:
        for i in range(len(INPUT_SLEWS)):
            row = res[key][i*n:(i+1)*n]
            if any(b < a for a, b in zip(row, row[1:])):
                problems.append(f"{key} non-monotonic in load @ slew idx {i}: {row}")
    if any(v <= 0 for v in res["tpLH"] + res["tpHL"]):
        problems.append("non-positive delay found")
    report = {"status": "PASS" if not problems else "FAIL", "problems": problems}
    (OUT / "qa_report.json").write_text(json.dumps(report, indent=2))
    print(f"QA: {report['status']}")
    for p in problems: print("  -", p)
    return report

if __name__ == "__main__":
    print("== TIMING & POWER characterization ==")
    res = characterize()
    print("== NOISE characterization ==")
    noise = characterize_noise()
    (OUT / "noise_report.json").write_text(json.dumps(noise, indent=2))
    print(f"  route glitch dip:      {noise['glitch_route']:.3f} V (quiet level = {VDD} V)")
    print(f"  receiver-out glitch:   {noise['glitch_vout']:.3f} V (receiver regenerates: glitch does not propagate)")
    print(f"  crosstalk delta delay: {noise['delta_delay']*1e12:.2f} ps")
    lib = write_lib(res)
    print(f"== Liberty written: {lib.name} ==")
    qa(res)
