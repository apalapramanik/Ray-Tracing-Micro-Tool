#!/usr/bin/env python3
"""
Ray Tracing Micro Tool — unified CLI
=====================================

Usage
-----
  python raytrace.py report  <experiment_dir> [--floorplan path/to/floorplan.json]
  python raytrace.py heatmap <experiment_dir> [--boresight 0]

Commands
--------
  report   Generate a self-contained interactive HTML report from snr_data.csv.
           Opens automatically in your browser when done.

  heatmap  Generate static SNR heatmap PNGs from snr_data.csv.
           Use --boresight to set TX boresight angle (degrees, default 0).
"""

import argparse
import sys
import os
import webbrowser
from pathlib import Path


# ── helpers ───────────────────────────────────────────────────────────────────

def _check_experiment_dir(path: str) -> Path:
    p = Path(path).resolve()
    if not p.is_dir():
        print(f"[ERROR] Directory not found: {p}")
        print("        Make sure you pass the folder that contains snr_data.csv")
        sys.exit(1)
    snr = p / "snr_data.csv"
    if not snr.exists():
        print(f"[ERROR] snr_data.csv not found inside: {p}")
        print("        Expected: {p / 'snr_data.csv'}")
        sys.exit(1)
    return p


def _default_floorplan() -> Path:
    """Return the floorplan JSON that lives next to this script."""
    here = Path(__file__).parent
    # Try the name used in the repo first, then fall back gracefully
    for name in ("nh_2ndfloor_floorplan.json", "floorplan.json", "control_plan.json"):
        candidate = here / name
        if candidate.exists():
            return candidate
    return here / "nh_2ndfloor_floorplan.json"   # will be caught by load_floorplan


# ── subcommands ───────────────────────────────────────────────────────────────

def cmd_report(args):
    """Generate an interactive HTML report."""
    experiment_dir = _check_experiment_dir(args.experiment_dir)
    floorplan_path = Path(args.floorplan) if args.floorplan else _default_floorplan()

    if args.floorplan and not floorplan_path.exists():
        print(f"[ERROR] Floorplan file not found: {floorplan_path}")
        sys.exit(1)

    if not floorplan_path.exists():
        print(f"[WARNING] No floorplan found at {floorplan_path}")
        print("          Report will be generated without floor plan overlay.")
        print("          Use --floorplan to specify one, or edit floorplan.html to create one.")

    # Import here so startup errors are shown immediately if deps are missing
    try:
        from generate_report import generate_report
    except ImportError as e:
        print(f"[ERROR] Could not import generate_report.py: {e}")
        print("        Run:  pip install -r requirements.txt")
        sys.exit(1)

    print(f"[ray tracing micro tool] Generating report for: {experiment_dir.name}")
    out_path = generate_report(str(experiment_dir), floorplan_path)

    print(f"[ray tracing micro tool] Done — opening in browser...")
    webbrowser.open(f"file://{out_path}")


def cmd_heatmap(args):
    """Generate static SNR heatmap PNGs."""
    experiment_dir = _check_experiment_dir(args.experiment_dir)

    try:
        from plot_heatmap import plotheatmap
    except ImportError as e:
        print(f"[ERROR] Could not import plot_heatmap.py: {e}")
        print("        Run:  pip install -r requirements.txt")
        sys.exit(1)

    # plotheatmap() tries to read .dat files for raw power; if they are absent
    # it fills with NaN gracefully. SNR heatmap only needs snr_data.csv.
    print(f"[ray tracing micro tool] Plotting heatmaps for: {experiment_dir.name}")
    print(f"                         TX boresight: {args.boresight} deg")
    plotheatmap(
        sweep_directory_path=str(experiment_dir),
        samples_per_beam=2000,
        tx_boresight_deg=args.boresight,
    )
    print(f"[ray tracing micro tool] Done — PNG/SVG files saved in {experiment_dir}")


# ── CLI setup ─────────────────────────────────────────────────────────────────

def build_parser():
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
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── report ──
    p_report = sub.add_parser(
        "report",
        help="Generate interactive HTML report (opens in browser)",
        description="Generate a self-contained HTML report from snr_data.csv.\n"
                    "The output file is saved inside the experiment directory.",
    )
    p_report.add_argument("experiment_dir", help="Folder containing snr_data.csv")
    p_report.add_argument(
        "--floorplan",
        default=None,
        metavar="PATH",
        help="Path to floorplan JSON (default: nh_2ndfloor_floorplan.json next to this script)",
    )
    p_report.set_defaults(func=cmd_report)

    # ── heatmap ──
    p_heat = sub.add_parser(
        "heatmap",
        help="Generate static SNR heatmap PNGs",
        description="Generate SNR and incident-angle heatmap PNGs from snr_data.csv.",
    )
    p_heat.add_argument("experiment_dir", help="Folder containing snr_data.csv")
    p_heat.add_argument(
        "--boresight",
        type=float,
        default=0.0,
        metavar="DEG",
        help="TX boresight angle in degrees (default: 0). "
             "0 = perpendicular to wall, positive = rotated right.",
    )
    p_heat.set_defaults(func=cmd_heatmap)

    return parser


def main():
    # Friendly message if no arguments given
    if len(sys.argv) == 1:
        build_parser().print_help()
        sys.exit(0)

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
