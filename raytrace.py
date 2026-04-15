#!/usr/bin/env python3
"""
raytrace.py — Ray Tracing Micro Tool, unified CLI entry point
=============================================================

This is the ONLY script you need to call directly. It delegates to:
  - generate_report.py  →  for the `report` subcommand
  - plot_heatmap.py     →  for the `heatmap` subcommand

Usage
-----
  python raytrace.py report  <experiment_dir> [--floorplan path/to/floorplan.json]
  python raytrace.py heatmap <experiment_dir> [--boresight 0]

Commands
--------
  report   Build a self-contained interactive HTML report from snr_data.csv.
           The report opens automatically in your browser when done.

  heatmap  Generate static SNR and incident-angle heatmap PNGs/SVGs.
           Use --boresight to set the TX boresight angle (degrees, default 0).

© 2025 Apala Pramanik · Concept: Dr. Mehmet C. Vuran · Built with Claude (Anthropic)
"""

import argparse
import sys
import os
import webbrowser
from pathlib import Path


# =============================================================================
# SECTION 1 — INPUT VALIDATION HELPERS
# =============================================================================
# These functions run before any heavy imports so errors are reported fast
# and clearly, even if numpy/pandas are not installed yet.

def _check_experiment_dir(path: str) -> Path:
    """
    Validate that the given path is a real directory containing snr_data.csv.

    Parameters
    ----------
    path : str
        The path the user passed on the command line.

    Returns
    -------
    Path
        Resolved absolute Path object for the experiment directory.

    Exits with a clear error message if:
      - the directory does not exist
      - snr_data.csv is not inside it
    """
    p = Path(path).resolve()

    # Check that the directory itself exists
    if not p.is_dir():
        print(f"[ERROR] Directory not found: {p}")
        print("        Make sure you pass the folder that contains snr_data.csv")
        sys.exit(1)

    # Check that snr_data.csv is inside — this is the only required input file
    snr = p / "snr_data.csv"
    if not snr.exists():
        print(f"[ERROR] snr_data.csv not found inside: {p}")
        print(f"        Expected: {p / 'snr_data.csv'}")
        sys.exit(1)

    return p


def _default_floorplan() -> Path:
    """
    Find the default floorplan JSON file next to this script.

    The function tries several common filenames in order:
      1. floorplan.json     (the repo default)
      2. control_plan.json  (legacy name)

    Returns
    -------
    Path
        Path to the first matching file, or floorplan.json
        (even if it doesn't exist — load_floorplan() handles the missing
        file gracefully by returning an empty floor plan).

    HOW TO CUSTOMISE:
        Add your own floorplan filename to the list below, or always pass
        --floorplan explicitly to avoid this lookup entirely.
    """
    here = Path(__file__).parent

    # Try each candidate filename in priority order
    for name in ("floorplan.json", "control_plan.json"):
        candidate = here / name
        if candidate.exists():
            return candidate

    # None found — return the default name so load_floorplan() can warn gracefully
    return here / "floorplan.json"


# =============================================================================
# SECTION 2 — SUBCOMMAND HANDLERS
# =============================================================================
# Each subcommand is a plain function that receives the parsed `args` namespace.
# Add a new subcommand by writing a new function here and registering it in
# build_parser() below.

def cmd_report(args):
    """
    Subcommand: `python raytrace.py report <experiment_dir>`

    Workflow
    --------
    1. Validate the experiment directory contains snr_data.csv
    2. Resolve which floorplan JSON to use (--floorplan or the default)
    3. Import generate_report and call generate_report()
    4. Open the resulting HTML file in the default browser

    HOW TO CUSTOMISE:
        - To skip auto-opening the browser, remove the webbrowser.open() call.
        - To change the default floorplan, edit _default_floorplan() above.
        - generate_report() returns the output file path as a string if you
          need it for downstream processing.
    """
    # Step 1 — validate inputs
    experiment_dir = _check_experiment_dir(args.experiment_dir)

    # Step 2 — resolve floorplan path
    # If the user passed --floorplan explicitly, use that; otherwise auto-detect
    floorplan_path = Path(args.floorplan) if args.floorplan else _default_floorplan()

    # If the user explicitly passed a floorplan that doesn't exist, that's an error
    if args.floorplan and not floorplan_path.exists():
        print(f"[ERROR] Floorplan file not found: {floorplan_path}")
        sys.exit(1)

    # If no floorplan was found at all, warn but continue — the report will
    # still render, just without any floor plan overlay
    if not floorplan_path.exists():
        print(f"[WARNING] No floorplan found at {floorplan_path}")
        print("          Report will be generated without floor plan overlay.")
        print("          Use --floorplan to specify one, or edit floorplan.html to create one.")

    # Step 3 — import generate_report (late import so missing deps are caught here)
    try:
        from generate_report import generate_report
    except ImportError as e:
        print(f"[ERROR] Could not import generate_report.py: {e}")
        print("        Run:  pip install -r requirements.txt")
        sys.exit(1)

    print(f"[ray tracing micro tool] Generating report for: {experiment_dir.name}")
    out_path = generate_report(str(experiment_dir), floorplan_path)

    # Step 4 — open in browser
    # webbrowser.open() uses file:// URI so the browser loads the local file
    print(f"[ray tracing micro tool] Done — opening in browser...")
    webbrowser.open(f"file://{out_path}")


def cmd_heatmap(args):
    """
    Subcommand: `python raytrace.py heatmap <experiment_dir>`

    Workflow
    --------
    1. Validate the experiment directory contains snr_data.csv
    2. Import plot_heatmap and call plotheatmap()
    3. PNG and SVG files are saved inside the experiment directory

    HOW TO CUSTOMISE:
        - Change `samples_per_beam` below if your hardware uses a different
          sample count (default 2000 matches the standard sweep configuration).
        - Pass --boresight to shift the incident-angle heatmap's Y-axis.
          0° = TX perpendicular to the wall (normal incidence).
          Positive = TX rotated clockwise (to the right).
    """
    # Step 1 — validate inputs
    experiment_dir = _check_experiment_dir(args.experiment_dir)

    # Step 2 — import plotheatmap (late import so missing deps are caught here)
    try:
        from plot_heatmap import plotheatmap
    except ImportError as e:
        print(f"[ERROR] Could not import plot_heatmap.py: {e}")
        print("        Run:  pip install -r requirements.txt")
        sys.exit(1)

    print(f"[ray tracing micro tool] Plotting heatmaps for: {experiment_dir.name}")
    print(f"                         TX boresight: {args.boresight} deg")

    # plotheatmap() also tries to read raw .dat IQ files (tx_beam_0.dat, etc.)
    # for power metrics. If those are absent (common when only snr_data.csv
    # is available), it fills the power matrix with NaN and still produces the
    # SNR and incident-angle heatmaps correctly.
    plotheatmap(
        sweep_directory_path=str(experiment_dir),
        samples_per_beam=2000,          # ← change this if your sweep uses a different count
        tx_boresight_deg=args.boresight,
    )

    print(f"[ray tracing micro tool] Done — PNG/SVG files saved in {experiment_dir}")


# =============================================================================
# SECTION 3 — CLI ARGUMENT PARSER
# =============================================================================
# All command-line arguments are defined here. To add a new subcommand:
#   1. Write a cmd_<name>(args) function in Section 2
#   2. Add a sub.add_parser(...) block below
#   3. Call p_<name>.set_defaults(func=cmd_<name>)

def build_parser():
    """
    Construct and return the argparse parser for the full CLI.

    Top-level structure:
        raytrace.py <COMMAND> [options]

    Subcommands:
        report   → cmd_report()
        heatmap  → cmd_heatmap()
    """
    parser = argparse.ArgumentParser(
        prog="raytrace",
        description="Ray Tracing Micro Tool — mmWave beam-sweep analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python raytrace.py report  my_experiment/
  python raytrace.py report  my_experiment/ --floorplan lab_floorplan.json
  python raytrace.py heatmap my_experiment/
  python raytrace.py heatmap my_experiment/ --boresight 45
        """,
    )

    # Each subcommand gets its own sub-parser under the `command` dest key
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True  # Print help (not a cryptic error) if no command is given

    # -------------------------------------------------------------------------
    # Subcommand: report
    # -------------------------------------------------------------------------
    p_report = sub.add_parser(
        "report",
        help="Generate interactive HTML report (opens in browser)",
        description="Generate a self-contained HTML report from snr_data.csv.\n"
                    "The output file is saved inside the experiment directory.",
    )
    # Positional: path to experiment folder (must contain snr_data.csv)
    p_report.add_argument(
        "experiment_dir",
        help="Folder containing snr_data.csv",
    )
    # Optional: path to a custom floorplan JSON (created with floorplan.html)
    p_report.add_argument(
        "--floorplan",
        default=None,
        metavar="PATH",
        help="Path to floorplan JSON (default: floorplan.json next to this script). "
             "Create one with floorplan.html.",
    )
    # Wire this subcommand to its handler function
    p_report.set_defaults(func=cmd_report)

    # -------------------------------------------------------------------------
    # Subcommand: heatmap
    # -------------------------------------------------------------------------
    p_heat = sub.add_parser(
        "heatmap",
        help="Generate static SNR heatmap PNGs",
        description="Generate SNR and incident-angle heatmap PNGs from snr_data.csv.",
    )
    # Positional: path to experiment folder (must contain snr_data.csv)
    p_heat.add_argument(
        "experiment_dir",
        help="Folder containing snr_data.csv",
    )
    # Optional: TX boresight angle for the incident-angle heatmap
    # 0° = TX is perpendicular to the wall (broadside / normal incidence)
    # A positive angle means the TX is rotated to the right relative to the wall normal
    p_heat.add_argument(
        "--boresight",
        type=float,
        default=0.0,
        metavar="DEG",
        help="TX boresight angle in degrees (default: 0). "
             "0 = perpendicular to wall, positive = rotated right.",
    )
    # Wire this subcommand to its handler function
    p_heat.set_defaults(func=cmd_heatmap)

    return parser


# =============================================================================
# SECTION 4 — ENTRY POINT
# =============================================================================

def main():
    """
    Parse arguments and dispatch to the appropriate subcommand handler.
    Prints help and exits cleanly if called with no arguments.
    """
    # Show help instead of an unhelpful error when called with no arguments
    if len(sys.argv) == 1:
        build_parser().print_help()
        sys.exit(0)

    parser = build_parser()
    args = parser.parse_args()

    # Each subcommand registered set_defaults(func=...) so we just call it
    args.func(args)


# Only run main() when this script is executed directly (not when imported)
if __name__ == "__main__":
    main()
