#!/usr/bin/env python3
"""
generate_report.py

Generate a self-contained HTML experiment report that combines:
  1. 63×63 beam-sweep SNR heatmap  (viridis, 6–25 dB)  — required: snr_data.csv
  2. Lab floor plan with TX/RX markers and best-beam visualisation
  3. Spatial SNR coverage overlay on the floor plan

Layout follows t6.html: left panel (info + mini heatmap), right full-height canvas.

Usage:
    /usr/bin/python3 generate_report.py <experiment_directory>
    /usr/bin/python3 generate_report.py <experiment_directory> --floorplan /path/to/floorplan.json

The output HTML is saved as:
    <experiment_directory>/<folder_name>.html

TX/RX positions are read from nh_2ndfloor_floorplan.json (keys "tx" and "rx" with
fields x, y, boresight_deg).  Edit that file before generating the report.
"""

import sys
import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# ── Beam geometry (must match plot_heatmap.py) ────────────────────────────────
NUM_BEAMS = 63

TX_ANGLES = [
     45.0, 43.5, 42.1, 40.6, 39.2, 37.7, 36.3, 34.8, 33.4, 31.9,
     30.5, 29.0, 27.6, 26.1, 24.7, 23.2, 21.8, 20.3, 18.9, 17.4,
     16.0, 14.5, 13.1, 11.6, 10.2,  8.7,  7.3,  5.8,  4.4,  2.9,
      1.5,  0.0, -1.5, -2.9, -4.4, -5.8, -7.3, -8.7,-10.2,-11.6,
    -13.1,-14.5,-16.0,-17.4,-18.9,-20.3,-21.8,-23.2,-24.7,-26.1,
    -27.6,-29.0,-30.5,-31.9,-33.4,-34.8,-36.3,-37.7,-39.2,-40.6,
    -42.1,-43.5,-45.0,
]

RX_ANGLES = [
    -45.0,-43.5,-42.1,-40.6,-39.2,-37.7,-36.3,-34.8,-33.4,-31.9,
    -30.5,-29.0,-27.6,-26.1,-24.7,-23.2,-21.8,-20.3,-18.9,-17.4,
    -16.0,-14.5,-13.1,-11.6,-10.2, -8.7, -7.3, -5.8, -4.4, -2.9,
     -1.5,  0.0,  1.5,  2.9,  4.4,  5.8,  7.3,  8.7, 10.2, 11.6,
     13.1, 14.5, 16.0, 17.4, 18.9, 20.3, 21.8, 23.2, 24.7, 26.1,
     27.6, 29.0, 30.5, 31.9, 33.4, 34.8, 36.3, 37.7, 39.2, 40.6,
     42.1, 43.5, 45.0,
]

# ── Data loaders ──────────────────────────────────────────────────────────────

def load_snr_matrix(sweep_dir: Path):
    """Return (NUM_BEAMS x NUM_BEAMS) SNR array from snr_data.csv. Exits if not found."""
    csv = sweep_dir / "snr_data.csv"
    if not csv.exists():
        print("[ERROR] snr_data.csv not found in:", sweep_dir)
        sys.exit(1)
    df = pd.read_csv(csv, header=None, names=["n", "tx", "rx", "snr"])
    mat = np.full((NUM_BEAMS, NUM_BEAMS), np.nan, dtype=float)
    for _, r in df.iterrows():
        ti, ri = int(r["tx"]), int(r["rx"])
        if ti < NUM_BEAMS and ri < NUM_BEAMS:
            mat[ti, ri] = r["snr"]
    return mat


def load_floorplan(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"walls": [], "tx": None, "rx": None}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _json_flat(arr: np.ndarray) -> str:
    parts = []
    for v in arr.flatten():
        if np.isnan(v):
            parts.append("null")
        else:
            parts.append(str(round(float(v), 3)))
    return "[" + ",".join(parts) + "]"


# ── Report generator ──────────────────────────────────────────────────────────

def generate_report(sweep_dir_str: str, floorplan_path: Path) -> str:
    sweep_dir = Path(sweep_dir_str).resolve()
    name = sweep_dir.name

    snr = load_snr_matrix(sweep_dir)
    fp  = load_floorplan(floorplan_path)

    bsi = int(np.nanargmax(np.nan_to_num(snr, nan=-np.inf)))
    bti, bri = divmod(bsi, NUM_BEAMS)
    bsnr = float(snr[bti, bri])
    btx, brx = TX_ANGLES[bti], RX_ANGLES[bri]

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    exp_obj = {
        "name":        name,
        "timestamp":   ts,
        "bestTxIdx":   int(bti),
        "bestRxIdx":   int(bri),
        "bestTxAngle": btx,
        "bestRxAngle": brx,
        "bestSnr":     round(bsnr, 2),
    }

    data_block = (
        f"const EXPERIMENT = {json.dumps(exp_obj, indent=2)};\n"
        f"const SNR_DATA   = {_json_flat(snr)};\n"
        f"const FLOORPLAN  = {json.dumps(fp)};\n"
        f"const TX_ANGLES  = {json.dumps(TX_ANGLES)};\n"
        f"const RX_ANGLES  = {json.dumps(RX_ANGLES)};\n"
        f"const NUM_BEAMS  = {NUM_BEAMS};\n"
    )

    html = (HTML_TEMPLATE
            .replace("/*__DATA_BLOCK__*/", data_block)
            .replace("__TITLE__", name)
            .replace("__TIMESTAMP__", ts))

    out = sweep_dir / f"{name}.html"
    out.write_text(html, encoding="utf-8")
    print(f"[Report] Saved → {out}")
    return str(out)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Generate beam-sweep HTML report")
    p.add_argument("experiment_dir", help="Path to the experiment folder")
    p.add_argument(
        "--floorplan",
        default=str(Path(__file__).parent / "control_plan.json"),
        help="Path to floorplan JSON (default: control_plan.json alongside this script)",
    )
    args = p.parse_args()
    generate_report(args.experiment_dir, Path(args.floorplan))


# ── HTML template ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ — Beam Sweep Report</title>
<style>
  :root { --bg:#0b0f14; --panel:#121a24; --text:#e7eef7; --muted:#9fb0c3; --line:#2a3a4e; --accent:#3a8fd4; }
  body { margin:0; font-family: 'Segoe UI', system-ui, -apple-system, Roboto, Arial, sans-serif; background:var(--bg); color:var(--text); }
  .wrap { display:flex; gap:10px; padding:10px; height:100vh; box-sizing:border-box; }
  .panel {
    width: 320px; min-width: 300px; background:var(--panel);
    border:1px solid #1b2a3b; border-radius:8px; padding:10px; box-sizing:border-box;
    display:flex; flex-direction:column; gap:6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    overflow-y: auto; max-height: 100vh;
  }
  .panel h1 {
    font-size:15px; margin:0 0 2px; font-weight:600;
    background: linear-gradient(135deg, #8fd4ff 0%, #5a9fd4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.3px;
  }
  .hint { font-size:10px; color:var(--muted); line-height:1.3; margin-bottom: 3px; }
  .row { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
  .control-group {
    background: rgba(10, 15, 21, 0.5); border-radius: 6px; padding: 7px;
    border: 1px solid rgba(42, 61, 82, 0.6);
    transition: all 0.2s;
  }
  .control-group:hover {
    background: rgba(10, 15, 21, 0.65);
    border-color: rgba(74, 125, 168, 0.4);
  }
  .control-group-title {
    font-size: 10px; color: #8fb4d4; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 5px; font-weight: 600;
    display: flex; align-items: center;
  }
  .control-group-title::before {
    content: '▸'; margin-right: 4px; color: #4a7da8; font-size: 8px;
  }
  .compact-row {
    display: grid; grid-template-columns: 42px 56px 32px 56px; gap: 4px;
    align-items: center; margin-bottom: 3px;
  }
  .compact-row.wide-label {
    grid-template-columns: 42px 56px 75px 56px;
  }
  .compact-row:last-child { margin-bottom: 0; }
  label {
    font-size:10px; color:#b5c7d9; font-weight:500;
    letter-spacing: 0.1px; white-space: nowrap;
  }
  .btn-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px;
  }
  .btn-grid-2 {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;
  }
  .stat {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size:9.5px; color:#c5d9eb; background:#0a0f15; padding:5px 7px;
    border-radius:4px; border:1px solid #1a2835; line-height:1.4;
  }
  .section-divider {
    height:1px; background:linear-gradient(90deg, transparent, #2a3d52 20%, #2a3d52 80%, transparent);
    margin:2px 0;
  }
  .canvasWrap {
    flex:1; background:#06090d; border:1px solid #142233; border-radius:10px; position:relative; overflow:hidden;
  }
  canvas { width:100%; height:100%; display:block; }
  .badge {
    position:absolute; left:10px; top:10px; background:rgba(18,26,36,0.92);
    border:1px solid #2a3d52; border-radius:8px; padding:8px 10px; font-size:10.5px; color:#b5c7d9;
    backdrop-filter: blur(8px); box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    display: flex; flex-direction: column; gap: 5px;
  }
  .badge strong { color: #d5e5f5; font-weight: 600; font-size: 11px; margin-bottom: 2px; }
  .legend-item {
    display: flex; align-items: center; gap: 6px; font-size: 10px;
  }
  .legend-icon {
    width: 28px; height: 14px; display: flex; align-items: center; justify-content: center;
    position: relative;
  }
  .legend-circle {
    width: 10px; height: 10px; border-radius: 50%;
  }
  .legend-line {
    width: 24px; height: 2px; border-radius: 1px;
  }
  .legend-line.dashed {
    background: linear-gradient(to right, currentColor 4px, transparent 4px) repeat-x;
    background-size: 8px 2px;
  }
  .scale-badge {
    position:absolute; right:10px; top:10px; background:rgba(18,26,36,0.92);
    border:1px solid #2a3d52; border-radius:8px; padding:10px 14px; font-size:11.5px; color:#b5c7d9;
    backdrop-filter: blur(8px); font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    line-height: 1.6; box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  }
  .scale-badge .title { color: #d5e5f5; font-weight: 600; margin-bottom: 5px; font-size: 12px; }
  .scale-badge .value { color: #8fd4ff; font-weight: 500; }
  .cursor-coords {
    position: absolute;
    background: rgba(18, 26, 36, 0.95);
    border: 1px solid #3a5878;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 11px;
    color: #8fd4ff;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s ease;
    z-index: 1000;
    white-space: nowrap;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }
  .cursor-coords.visible {
    opacity: 1;
  }
  /* Beam Sweep Data panel */
  .snr-heatmap-wrap { position:relative; border:1px solid rgba(42,61,82,0.8); border-radius:4px; overflow:hidden; margin-bottom:5px; }
  #snrMiniCanvas { display:block; width:100%; image-rendering:pixelated; cursor:crosshair; }
  .snr-axis-label { font-size:9px; color:var(--muted); text-align:center; }
  .snr-axis-row { display:flex; justify-content:space-between; padding:0 2px; }
  .snr-readout { display:flex; justify-content:space-between; align-items:center; margin-top:4px; flex-wrap:wrap; gap:3px; }
  .snr-angles { font-size:10px; color:var(--muted); font-family:ui-monospace,monospace; }
  .snr-value-box { font-size:12px; font-weight:700; font-family:ui-monospace,monospace; padding:2px 7px; border-radius:4px; background:rgba(10,15,21,0.7); border:1px solid rgba(42,61,82,0.8); }
  .snr-best { font-size:9px; color:var(--muted); margin-top:2px; }
  .snr-best span { color:#8fd4ff; }
  .snr-colorbar { display:flex; align-items:center; gap:4px; margin-top:3px; }
  .snr-colorbar-grad { flex:1; height:6px; border-radius:3px; }
  .snr-colorbar-labels { display:flex; justify-content:space-between; font-size:8px; color:var(--muted); }
</style>
</head>
<body>
<div class="wrap">

  <!-- ── Left Panel ── -->
  <div class="panel">
    <h1>__TITLE__</h1>
    <div class="hint">__TIMESTAMP__</div>

    <div class="section-divider"></div>

    <!-- Experiment Info -->
    <div class="control-group">
      <div class="control-group-title">Experiment Name</div>
      <div style="display:flex;flex-direction:column;gap:4px;">
        <div style="font-size:12px;font-weight:600;color:#c8dff0;letter-spacing:-0.2px;word-break:break-all;" id="expName">--</div>
        <div style="height:1px;background:rgba(42,61,82,0.5);margin:1px 0;"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
          <div style="background:#0a0f15;border:1px solid #1a2d40;border-radius:5px;padding:5px 7px;">
            <div style="font-size:8px;color:#5a8aaa;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Date</div>
            <div style="font-size:11px;color:#c5d9eb;font-family:ui-monospace,monospace;" id="expDate">--</div>
          </div>
          <div style="background:#0a0f15;border:1px solid #1a2d40;border-radius:5px;padding:5px 7px;">
            <div style="font-size:8px;color:#5a8aaa;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Time</div>
            <div style="font-size:11px;color:#c5d9eb;font-family:ui-monospace,monospace;" id="expTime">--</div>
          </div>
        </div>
        <div style="background:linear-gradient(135deg,rgba(58,143,212,0.12),rgba(31,158,137,0.10));border:1px solid rgba(58,143,212,0.25);border-radius:6px;padding:7px 10px;display:flex;align-items:center;justify-content:space-between;">
          <div>
            <div style="font-size:8px;color:#5a8aaa;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Best SNR</div>
            <div style="font-size:18px;font-weight:700;font-family:ui-monospace,monospace;letter-spacing:-0.5px;" id="expBestSnr">--</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:8px;color:#5a8aaa;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Beam Pair</div>
            <div style="font-size:10px;font-family:ui-monospace,monospace;color:#8fd4ff;" id="expBeamPair">--</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Beam Parameters -->
    <div class="control-group">
      <div class="control-group-title">Beam Parameters</div>
      <div class="compact-row wide-label">
        <label>Best TX</label>
        <span id="txBestVal" style="font-size:11px;color:var(--text);background:#0d1419;border:1px solid #2a3d52;border-radius:3px;padding:3px 5px;font-family:ui-monospace,monospace;">--</span>
        <label>Best RX</label>
        <span id="rxBestVal" style="font-size:11px;color:var(--text);background:#0d1419;border:1px solid #2a3d52;border-radius:3px;padding:3px 5px;font-family:ui-monospace,monospace;">--</span>
      </div>
      <div style="margin-top:6px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
          <label>Beam Length</label>
          <span id="beamLenLabel" style="font-size:10px;color:#8fd4ff;font-family:ui-monospace,monospace;">1.0×</span>
        </div>
        <input id="beamLenSlider" type="range" min="0.2" max="4" step="0.05" value="1"
          style="width:100%;accent-color:#3a8fd4;cursor:pointer;">
      </div>
    </div>

    <!-- Beam Sweep Data (SNR) -->
    <div class="control-group">
      <div class="control-group-title">Beam Sweep Data (SNR)</div>
      <div class="hint">Live SNR lookup from 63×63 beam sweep · axes = relative angle</div>
      <div class="snr-axis-label" style="text-align:right;padding-right:2px;">RX Rel Angle →</div>
      <div style="display:flex;gap:3px;align-items:flex-start;">
        <div style="writing-mode:vertical-rl;transform:rotate(180deg);font-size:9px;color:var(--muted);align-self:center;white-space:nowrap;">TX Rel Angle →</div>
        <div style="flex:1;">
          <div class="snr-heatmap-wrap">
            <canvas id="snrMiniCanvas" width="189" height="189"></canvas>
          </div>
          <div class="snr-axis-row">
            <span class="snr-axis-label">-45°</span>
            <span class="snr-axis-label">0°</span>
            <span class="snr-axis-label">+45°</span>
          </div>
        </div>
      </div>
      <div class="snr-colorbar">
        <span style="font-size:8px;color:var(--muted);">6 dB</span>
        <div class="snr-colorbar-grad" id="snrCbarGrad"></div>
        <span style="font-size:8px;color:var(--muted);">25 dB</span>
      </div>
      <div class="snr-readout">
        <span class="snr-angles" id="snrAngles">TX --° / RX --°</span>
        <span class="snr-value-box" id="snrValueBox" style="color:#aaa;">-- dB</span>
      </div>
      <div class="snr-best">Best: <span id="snrBestInfo"></span></div>
    </div>

    <div class="stat" id="statBar"> </div>
  </div>

  <!-- ── Right Canvas ── -->
  <div class="canvasWrap" id="canvasWrap">
    <div class="badge">
      <strong>Legend</strong>
      <div class="legend-item">
        <div class="legend-icon">
          <div class="legend-circle" style="background: rgba(0, 220, 255, 0.9);"></div>
        </div>
        <span>TX</span>
      </div>
      <div class="legend-item">
        <div class="legend-icon">
          <div class="legend-circle" style="background: rgba(255, 170, 60, 0.9);"></div>
        </div>
        <span>RX</span>
      </div>
      <div class="legend-item">
        <div class="legend-icon">
          <div class="legend-line dashed" style="color: rgba(180, 220, 255, 0.8);"></div>
        </div>
        <span>Boresight</span>
      </div>
      <div class="legend-item">
        <div class="legend-icon">
          <div class="legend-line" style="background: rgba(180, 220, 255, 0.95);"></div>
        </div>
        <span>Best Beam</span>
      </div>
      <div class="legend-item">
        <div class="legend-icon">
          <div class="legend-line" style="background: rgba(160, 160, 160, 0.8);"></div>
        </div>
        <span>Wall</span>
      </div>
      <div class="legend-item">
        <div class="legend-icon">
          <div class="legend-line" style="background: rgba(180, 220, 255, 0.35);"></div>
        </div>
        <span>Reflection</span>
      </div>
      <div style="font-size:9px;color:var(--muted);margin-top:4px;padding-top:4px;border-top:1px solid rgba(42,61,82,0.5);">2 px = 1 inch · grid = 12.5 in</div>
    </div>

    <div class="cursor-coords" id="cursorCoords"></div>
    <div style="position:absolute;right:10px;bottom:10px;display:flex;gap:6px;align-items:center;z-index:10;">
      <span id="zoomLabel" style="font-size:11px;color:#8fd4ff;font-family:ui-monospace,monospace;background:rgba(18,26,36,0.92);border:1px solid #2a3d52;border-radius:6px;padding:4px 8px;">1.0x</span>
      <button id="zoomResetBtn" style="font-size:10px;color:#b5c7d9;background:rgba(18,26,36,0.92);border:1px solid #2a3d52;border-radius:6px;padding:4px 10px;cursor:pointer;font-family:system-ui,sans-serif;" onmouseover="this.style.borderColor='#3a8fd4'" onmouseout="this.style.borderColor='#2a3d52'">Reset</button>
    </div>
    <canvas id="c"></canvas>
  </div>

</div>
<script>
/*__DATA_BLOCK__*/

// ── Viridis colormap (SNR_MIN=6, SNR_MAX=25) ─────────────────────────────────
const SNR_MIN = 6, SNR_MAX = 25;
const VIRIDIS = [
  [68,1,84],[72,40,120],[62,83,160],[49,104,142],[38,130,142],[31,158,137],
  [53,183,121],[110,206,88],[180,222,44],[253,231,37]
];
function snrToRgb(snr) {
  const t = Math.max(0, Math.min(0.9999, (snr - SNR_MIN) / (SNR_MAX - SNR_MIN)));
  const n = VIRIDIS.length - 1;
  const lo = Math.floor(t * n), hi = Math.min(lo + 1, n);
  const f = t * n - lo;
  return VIRIDIS[lo].map((c, i) => Math.round(c + f * (VIRIDIS[hi][i] - c)));
}
function snrToColor(snr, alpha) { const [r,g,b] = snrToRgb(snr); return `rgba(${r},${g},${b},${alpha ?? 1})`; }

// ── Floor-plan transform ──────────────────────────────────────────────────────
const FP_X0 = 200, FP_Y0 = 200, FP_W = 644, FP_H = 520;

// Zoom & pan state
let zoomLevel = 1.0;
let panX = 0, panY = 0;
let isPanning = false, panStartX = 0, panStartY = 0, panStartPanX = 0, panStartPanY = 0;

function fpScale(W, H) {
  const padH = 90, padV = 90;
  const baseS = Math.min((W - padH*2) / FP_W, (H - padV*2) / FP_H);
  const s = baseS * zoomLevel;
  const ox = (W - FP_W*baseS) / 2 + panX;
  const oy = (H - FP_H*baseS) / 2 + panY;
  return { s, ox, oy };
}
function w2c(wx, wy, s, ox, oy) { return [(wx - FP_X0)*s + ox, (wy - FP_Y0)*s + oy]; }
function c2w(cx, cy, s, ox, oy) { return [(cx - ox)/s + FP_X0, (cy - oy)/s + FP_Y0]; }

// ── Angle helpers ─────────────────────────────────────────────────────────────
const norm360 = (d) => ((d % 360) + 360) % 360;
const norm180 = (d) => { let a = norm360(d); if (a > 180) a -= 360; return a; };
function normDeg(d) { d = ((d%360)+360)%360; return d > 180 ? d-360 : d; }

function findClosestBeam(angles, deg) {
  let best = 0, bestD = Infinity;
  for (let i = 0; i < angles.length; i++) {
    const d = Math.abs(angles[i] - deg);
    if (d < bestD) { bestD = d; best = i; }
  }
  return best;
}

// ── Canvas setup ──────────────────────────────────────────────────────────────
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let W = 0, H = 0;

// ── Selected beam state (updated from heatmap hover) ─────────────────────────
let currentTi = null, currentRi = null;

// ── Beam length scale (controlled by slider) ──────────────────────────────────
let beamLenScale = 1.0;

// ── drawCoordinateSystem ──────────────────────────────────────────────────────
function drawCoordinateSystem() {
  const margin = 20;
  const axisLength = 50;
  const originX = margin + 15;
  const originY = H - margin - 75;  // origin near top of box; Y arrow goes down

  ctx.save();

  // Semi-transparent background
  ctx.fillStyle = 'rgba(18, 26, 36, 0.80)';
  ctx.fillRect(margin, H - margin - 95, 92, 95);

  // Draw origin point
  ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
  ctx.beginPath();
  ctx.arc(originX, originY, 3, 0, Math.PI * 2);
  ctx.fill();

  // X-axis (red/orange) → right
  const xColor = 'rgba(255, 100, 100, 0.95)';
  ctx.strokeStyle = xColor;
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';

  ctx.beginPath();
  ctx.moveTo(originX, originY);
  ctx.lineTo(originX + axisLength, originY);
  ctx.stroke();

  const xTipX = originX + axisLength;
  const xTipY = originY;
  ctx.fillStyle = xColor;
  ctx.beginPath();
  ctx.moveTo(xTipX, xTipY);
  ctx.lineTo(xTipX - 8, xTipY - 4);
  ctx.lineTo(xTipX - 8, xTipY + 4);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = xColor;
  ctx.font = 'bold 12px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('+X', xTipX + 10, xTipY + 4);

  // Y-axis (green) ↓ downward — JSON Y increases downward
  const yColor = 'rgba(100, 255, 100, 0.95)';
  ctx.strokeStyle = yColor;
  ctx.lineWidth = 2.5;

  ctx.beginPath();
  ctx.moveTo(originX, originY);
  ctx.lineTo(originX, originY + axisLength);
  ctx.stroke();

  const yTipX = originX;
  const yTipY = originY + axisLength;
  ctx.fillStyle = yColor;
  ctx.beginPath();
  ctx.moveTo(yTipX, yTipY);
  ctx.lineTo(yTipX - 4, yTipY - 8);
  ctx.lineTo(yTipX + 4, yTipY - 8);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = yColor;
  ctx.font = 'bold 12px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('+Y', yTipX, yTipY + 13);

  ctx.restore();
}

// ── drawGrid ──────────────────────────────────────────────────────────────────
function drawGrid(step) {
  if (!step) return;
  ctx.save();
  ctx.strokeStyle = 'rgba(70, 100, 130, 0.18)';
  ctx.lineWidth = 1;
  for (let x = 0; x <= W; x += step) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  for (let y = 0; y <= H; y += step) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
  ctx.restore();

  // Draw scale indicator in bottom-left corner (above coordinate axes box)
  const margin = 20;
  const boxSize = step;
  const startX = margin;
  const startY = H - margin - 95 - boxSize - 60;

  ctx.save();
  ctx.fillStyle = 'rgba(18, 26, 36, 0.75)';
  ctx.fillRect(startX - 10, startY - 10, boxSize + 20, boxSize + 35);

  ctx.strokeStyle = 'rgba(143, 212, 255, 0.9)';
  ctx.lineWidth = 2;
  ctx.strokeRect(startX, startY, boxSize, boxSize);

  ctx.strokeStyle = 'rgba(143, 212, 255, 0.6)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(startX, startY + boxSize + 8);
  ctx.lineTo(startX + boxSize, startY + boxSize + 8);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(startX - 8, startY);
  ctx.lineTo(startX - 8, startY + boxSize);
  ctx.stroke();

  ctx.fillStyle = 'rgba(143, 212, 255, 1)';
  ctx.font = '11px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';
  ctx.textAlign = 'center';
  ctx.fillText(`${step.toFixed(0)}px`, startX + boxSize / 2, startY + boxSize + 20);

  ctx.restore();
}

// ── drawPoint ─────────────────────────────────────────────────────────────────
function drawPoint(p, color, label, wx, wy) {
  ctx.save();
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, Math.PI*2); ctx.fill();
  ctx.font = '12px system-ui, sans-serif';
  ctx.fillStyle = 'rgba(231,238,247,0.92)';
  ctx.fillText(label, p.x + 10, p.y - 10);
  ctx.font = '11px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace';
  ctx.fillStyle = 'rgba(159,176,195,0.95)';
  const coordStr = (wx !== undefined && wy !== undefined)
    ? `(${wx.toFixed(0)}, ${wy.toFixed(0)})`
    : `(${p.x.toFixed(1)}, ${p.y.toFixed(1)})`;
  ctx.fillText(coordStr, p.x + 10, p.y + 6);
  ctx.restore();
}

// ── drawArrow ─────────────────────────────────────────────────────────────────
function drawArrow(from, to, color, dashed=false, width=3, alpha=1.0) {
  const dx = to.x - from.x, dy = to.y - from.y;
  const ang = Math.atan2(dy, dx);

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  if (dashed) ctx.setLineDash([7,6]);

  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.stroke();

  const headLen = 14;
  const a1 = ang + Math.PI * 0.85;
  const a2 = ang - Math.PI * 0.85;

  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(to.x, to.y);
  ctx.lineTo(to.x + Math.cos(a1)*headLen, to.y + Math.sin(a1)*headLen);
  ctx.lineTo(to.x + Math.cos(a2)*headLen, to.y + Math.sin(a2)*headLen);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = 'rgba(255,255,255,0.10)';
  ctx.beginPath(); ctx.arc(to.x, to.y, 10, 0, Math.PI*2); ctx.fill();

  ctx.restore();
}

// ── drawFloorplanWall ─────────────────────────────────────────────────────────
function drawFloorplanWall(seg) {
  ctx.save();
  ctx.strokeStyle = 'rgba(255, 200, 100, 0.55)';
  ctx.lineWidth = 6;
  ctx.lineCap = 'round';
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(seg.ax, seg.ay);
  ctx.lineTo(seg.bx, seg.by);
  ctx.stroke();
  ctx.restore();
}

// ── drawBeamRangeFan ──────────────────────────────────────────────────────────
// Draws a single ±45° sector around boresight to show the beam sweep range
function drawBeamRangeFan(center, boresightDeg, radius, color) {
  const startRad = (boresightDeg - 45) * Math.PI / 180;
  const endRad   = (boresightDeg + 45) * Math.PI / 180;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(center.x, center.y);
  ctx.arc(center.x, center.y, radius, startRad, endRad);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
  // Arc border
  ctx.strokeStyle = color.replace(/[\d.]+\)$/, '0.4)');
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.restore();
}

// ── drawWallLabel ─────────────────────────────────────────────────────────────
function drawWallLabel(ax, ay, bx, by, fpAx, fpAy, fpBx, fpBy) {
  const lenFp = Math.hypot(fpBx - fpAx, fpBy - fpAy);
  const lenIn = lenFp / 2;
  if (lenIn < 4) return;  // skip tiny stubs

  const mx = (ax + bx) / 2, my = (ay + by) / 2;
  const dx = bx - ax, dy = by - ay;
  const wallLen = Math.hypot(dx, dy) || 1;

  // Perpendicular offset (8px, choose side that avoids going off-canvas centre)
  const nx = -dy / wallLen, ny = dx / wallLen;
  const ox = nx * 10, oy = ny * 10;

  const label = lenIn % 1 === 0 ? `${lenIn}"` : `${lenIn.toFixed(1)}"`;

  ctx.save();
  ctx.font = '9px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  // Small pill background
  const tw = ctx.measureText(label).width + 6;
  ctx.fillStyle = 'rgba(10, 15, 22, 0.72)';
  ctx.beginPath();
  ctx.roundRect(mx + ox - tw/2, my + oy - 7, tw, 14, 3);
  ctx.fill();
  ctx.fillStyle = 'rgba(200, 220, 240, 0.85)';
  ctx.fillText(label, mx + ox, my + oy);
  ctx.restore();
}

// ── raySegmentIntersection ────────────────────────────────────────────────────
function raySegmentIntersection(p, r, a, b) {
  const s = { x: b.x - a.x, y: b.y - a.y };
  const rxs = r.x * s.y - r.y * s.x;
  const q_p = { x: a.x - p.x, y: a.y - p.y };
  const qpxr = q_p.x * r.y - q_p.y * r.x;

  if (Math.abs(rxs) < 1e-9) return null;

  const t = (q_p.x * s.y - q_p.y * s.x) / rxs;
  const u = qpxr / rxs;

  if (t >= 0 && u >= 0 && u <= 1) {
    return { t, u, x: p.x + t * r.x, y: p.y + t * r.y };
  }
  return null;
}

// ── reflectDirection ──────────────────────────────────────────────────────────
function reflectDirection(dir, a, b) {
  const wx = b.x - a.x, wy = b.y - a.y;
  const wLen = Math.hypot(wx, wy) || 1;
  const txv = wx / wLen, tyv = wy / wLen;
  const nxv = -tyv, nyv = txv;

  const dLen = Math.hypot(dir.x, dir.y) || 1;
  const dx = dir.x / dLen, dy = dir.y / dLen;

  const dot = dx * nxv + dy * nyv;
  const rx = dx - 2 * dot * nxv;
  const ry = dy - 2 * dot * nyv;
  return { x: rx, y: ry };
}

// ── drawSpecularReflection ────────────────────────────────────────────────────
function drawSpecularReflection(origin, angleRad, length, wallsList, color) {
  if (!wallsList.length) return;

  const dir = { x: Math.cos(angleRad), y: Math.sin(angleRad) };
  let best = null, bestWall = null;

  for (const w of wallsList) {
    const a = { x: w.ax, y: w.ay }, b = { x: w.bx, y: w.by };
    const hit = raySegmentIntersection(origin, dir, a, b);
    if (!hit) continue;
    if (hit.t <= length + 1e-6) {
      if (!best || hit.t < best.t) { best = hit; bestWall = w; }
    }
  }

  if (!best || !bestWall) return;

  ctx.save();
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.beginPath(); ctx.arc(best.x, best.y, 4, 0, Math.PI * 2); ctx.fill();
  ctx.restore();

  const remaining = Math.max(0, length - best.t);
  if (remaining <= 1e-6) return;

  const a = { x: bestWall.ax, y: bestWall.ay }, b = { x: bestWall.bx, y: bestWall.by };
  const rdir = reflectDirection(dir, a, b);
  const end = { x: best.x + rdir.x * remaining, y: best.y + rdir.y * remaining };

  drawArrow({ x: best.x, y: best.y }, end, color, false, 2, 0.45);
}

// ── drawSNRFan ────────────────────────────────────────────────────────────────
// selectedIdx: the active beam index to highlight (brighter fill + white border)
function drawSNRFan(center, boresightDeg, snrRowFn, radius, selectedIdx) {
  const step = 90 / (NUM_BEAMS - 1);
  const halfStep = step / 2;
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';

  // Pass 1: dim background wedges
  for (let i = 0; i < NUM_BEAMS; i++) {
    if (i === selectedIdx) continue;
    const relDeg = -45 + i * step;
    const centerDeg = boresightDeg + relDeg;
    const startRad = centerDeg * Math.PI / 180 - halfStep * Math.PI / 180;
    const endRad   = centerDeg * Math.PI / 180 + halfStep * Math.PI / 180;
    const snr = snrRowFn(i);
    if (snr === null || snr === undefined) continue;
    const [r, g, b] = snrToRgb(snr);
    ctx.beginPath();
    ctx.moveTo(center.x, center.y);
    ctx.arc(center.x, center.y, radius, startRad, endRad);
    ctx.closePath();
    ctx.fillStyle = `rgba(${r},${g},${b},0.18)`;
    ctx.fill();
  }

  // Outer ring
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.lineWidth = 0.5;
  ctx.beginPath();
  ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
  ctx.stroke();

  // Pass 2: highlighted selected wedge on top
  if (selectedIdx !== undefined && selectedIdx !== null) {
    const relDeg = -45 + selectedIdx * step;
    const centerDeg = boresightDeg + relDeg;
    const startRad = centerDeg * Math.PI / 180 - halfStep * Math.PI / 180;
    const endRad   = centerDeg * Math.PI / 180 + halfStep * Math.PI / 180;
    const snr = snrRowFn(selectedIdx);
    if (snr !== null && snr !== undefined) {
      const [r, g, b] = snrToRgb(snr);
      ctx.beginPath();
      ctx.moveTo(center.x, center.y);
      ctx.arc(center.x, center.y, radius, startRad, endRad);
      ctx.closePath();
      ctx.fillStyle = `rgba(${r},${g},${b},0.75)`;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.70)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }
  ctx.restore();
}

// ── buildCoverage ─────────────────────────────────────────────────────────────
function buildCoverage(W, H, s, ox, oy) {
  const tx = FLOORPLAN.tx;
  if (!tx || tx.x === null || tx.boresight_deg === null) return null;
  const STEP = 3;
  const W2 = Math.ceil(W/STEP), H2 = Math.ceil(H/STEP);
  const off = new OffscreenCanvas(W2, H2);
  const oc  = off.getContext('2d');
  const img = oc.createImageData(W2, H2);
  const d   = img.data;
  const txBore = tx.boresight_deg;
  const rx = FLOORPLAN.rx;
  const rxBore = (rx && rx.boresight_deg !== null) ? rx.boresight_deg : null;

  for (let iy = 0; iy < H2; iy++) {
    for (let ix = 0; ix < W2; ix++) {
      const wx = (ix*STEP + STEP/2 - ox)/s + FP_X0;
      const wy = (iy*STEP + STEP/2 - oy)/s + FP_Y0;
      const dx = wx - tx.x, dy = wy - tx.y;
      if (Math.sqrt(dx*dx+dy*dy) < 2) continue;
      const txRel = normDeg(Math.atan2(dy, dx)*180/Math.PI - txBore);
      const angToTX = Math.atan2(-dy, -dx)*180/Math.PI;
      const rxBoreCalc = rxBore !== null ? rxBore : normDeg(angToTX + 180);
      const rxRel = normDeg(angToTX - rxBoreCalc);
      const snr = SNR_DATA[findClosestBeam(TX_ANGLES, txRel)*NUM_BEAMS + findClosestBeam(RX_ANGLES, rxRel)];
      const pidx = (iy*W2 + ix)*4;
      if (snr === null || snr === undefined) { d[pidx+3]=0; continue; }
      const [r, g, b] = snrToRgb(snr);
      d[pidx]=r; d[pidx+1]=g; d[pidx+2]=b; d[pidx+3]=185;
    }
  }
  oc.putImageData(img, 0, 0);
  const full = new OffscreenCanvas(W, H);
  const fc = full.getContext('2d');
  fc.imageSmoothingEnabled = false;
  fc.drawImage(off, 0, 0, W, H);
  return full;
}

// ── draw ──────────────────────────────────────────────────────────────────────
function draw() {
  ctx.clearRect(0, 0, W, H);

  // 1. Background radial gradient
  const g = ctx.createRadialGradient(W*0.5, H*0.4, 40, W*0.5, H*0.5, Math.max(W, H));
  g.addColorStop(0, 'rgba(18,26,36,0.25)');
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);

  // 2. Grid (25 floor-plan px step)
  const { s, ox, oy } = fpScale(W, H);
  drawGrid(25 * s);

  // 3. Coordinate system axes
  drawCoordinateSystem();

  const tx = FLOORPLAN.tx;
  const rx = FLOORPLAN.rx;
  const hasTx = tx && tx.x !== null && tx.boresight_deg !== null;
  const hasRx = rx && rx.x !== null && rx.boresight_deg !== null;

  const txCanvas = hasTx ? { x: w2c(tx.x, tx.y, s, ox, oy)[0], y: w2c(tx.x, tx.y, s, ox, oy)[1] } : null;
  const rxCanvas = hasRx ? { x: w2c(rx.x, rx.y, s, ox, oy)[0], y: w2c(rx.x, rx.y, s, ox, oy)[1] } : null;

  // 4. Selected beam indices
  const selTi = currentTi !== null ? currentTi : EXPERIMENT.bestTxIdx;
  const selRi = currentRi !== null ? currentRi : EXPERIMENT.bestRxIdx;

  // 5. Beam sweep range fans (±45° sector showing scan coverage)
  const fanR = Math.min(W, H) * 0.18;
  if (hasTx) drawBeamRangeFan(txCanvas, tx.boresight_deg, fanR, 'rgba(0,220,255,0.07)');
  if (hasRx) drawBeamRangeFan(rxCanvas, rx.boresight_deg, fanR, 'rgba(255,170,60,0.07)');

  // 6. Floor plan walls (amber) + length labels
  for (const w of (FLOORPLAN.walls || [])) {
    const [ax, ay] = w2c(w.ax, w.ay, s, ox, oy);
    const [bx, by] = w2c(w.bx, w.by, s, ox, oy);
    drawFloorplanWall({ ax, ay, bx, by });
    drawWallLabel(ax, ay, bx, by, w.ax, w.ay, w.bx, w.by);
  }

  // 7. Dashed TX-RX link
  if (hasTx && hasRx) {
    ctx.save();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.10)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 6]);
    ctx.beginPath(); ctx.moveTo(txCanvas.x, txCanvas.y); ctx.lineTo(rxCanvas.x, rxCanvas.y); ctx.stroke();
    ctx.restore();
  }

  // 8. TX/RX drawPoint
  if (hasTx) drawPoint(txCanvas, 'rgba(0,220,255,0.95)', 'TX', tx.x, tx.y);
  if (hasRx) drawPoint(rxCanvas, 'rgba(255,170,60,0.95)', 'RX', rx.x, rx.y);

  // 9. Boresight + beam arrows
  if (hasTx && hasRx) {
    const baseLen = Math.hypot(rxCanvas.x - txCanvas.x, rxCanvas.y - txCanvas.y) * 1.5;
    const beamLen = baseLen * beamLenScale;
    const borLen  = baseLen * 0.45;
    const selSnr = SNR_DATA[selTi * NUM_BEAMS + selRi];
    const beamColor = (selSnr !== null && selSnr !== undefined)
      ? snrToColor(selSnr, 0.95)
      : 'rgba(180,220,255,0.95)';

    const txBoreRad = tx.boresight_deg * Math.PI / 180;
    const txBeamRad = (tx.boresight_deg + TX_ANGLES[selTi]) * Math.PI / 180;
    const txBoreHead = { x: txCanvas.x + Math.cos(txBoreRad) * borLen, y: txCanvas.y + Math.sin(txBoreRad) * borLen };
    const txBeamHead = { x: txCanvas.x + Math.cos(txBeamRad) * beamLen, y: txCanvas.y + Math.sin(txBeamRad) * beamLen };
    drawArrow(txCanvas, txBoreHead, 'rgba(0,220,255,0.55)', true, 2, 1.0);
    drawArrow(txCanvas, txBeamHead, beamColor, false, 3, 1.0);
    const allWalls = (FLOORPLAN.walls || []).map(w => {
      const [ax, ay] = w2c(w.ax, w.ay, s, ox, oy);
      const [bx, by] = w2c(w.bx, w.by, s, ox, oy);
      return { ax, ay, bx, by };
    });
    drawSpecularReflection(txCanvas, txBeamRad, beamLen, allWalls, beamColor);

    const rxBoreRad = rx.boresight_deg * Math.PI / 180;
    const rxBeamRad = (rx.boresight_deg + RX_ANGLES[selRi]) * Math.PI / 180;
    const rxBoreHead = { x: rxCanvas.x + Math.cos(rxBoreRad) * borLen, y: rxCanvas.y + Math.sin(rxBoreRad) * borLen };
    const rxBeamHead = { x: rxCanvas.x + Math.cos(rxBeamRad) * beamLen, y: rxCanvas.y + Math.sin(rxBeamRad) * beamLen };
    drawArrow(rxCanvas, rxBoreHead, 'rgba(255,170,60,0.55)', true, 2, 1.0);
    drawArrow(rxCanvas, rxBeamHead, beamColor, false, 3, 1.0);
    drawSpecularReflection(rxCanvas, rxBeamRad, beamLen, allWalls, beamColor);
  }

}

// ── resize ────────────────────────────────────────────────────────────────────
function resize() {
  const r = canvas.getBoundingClientRect();
  W = Math.max(1, Math.floor(r.width));
  H = Math.max(1, Math.floor(r.height));
  canvas.width = W * devicePixelRatio;
  canvas.height = H * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  draw();
}
window.addEventListener('resize', () => { clearTimeout(window._rsTimer); window._rsTimer = setTimeout(resize, 150); });

// ── Cursor coordinates ────────────────────────────────────────────────────────
canvas.addEventListener('mousemove', (ev) => {
  const rect = canvas.getBoundingClientRect();
  const { s, ox, oy } = fpScale(W, H);
  const [wx, wy] = c2w(ev.clientX - rect.left, ev.clientY - rect.top, s, ox, oy);
  const el = document.getElementById('cursorCoords');
  el.textContent = `x: ${wx.toFixed(1)}, y: ${wy.toFixed(1)}`;

  const offsetX = 15, offsetY = 15;
  let tooltipX = ev.clientX - rect.left + offsetX;
  let tooltipY = ev.clientY - rect.top + offsetY;
  const tooltipWidth = 120, tooltipHeight = 30;
  if (tooltipX + tooltipWidth > W) tooltipX = ev.clientX - rect.left - tooltipWidth - 5;
  if (tooltipY + tooltipHeight > H) tooltipY = ev.clientY - rect.top - tooltipHeight - 5;
  el.style.left = tooltipX + 'px';
  el.style.top  = tooltipY + 'px';
});
canvas.addEventListener('mouseenter', () => { document.getElementById('cursorCoords').classList.add('visible'); });
canvas.addEventListener('mouseleave', () => {
  document.getElementById('cursorCoords').classList.remove('visible');
  if (isPanning) isPanning = false;
});

// ── Zoom (mouse wheel) ──────────────────────────────────────────────────────
canvas.addEventListener('wheel', (ev) => {
  ev.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
  const oldZoom = zoomLevel;
  const factor = ev.deltaY < 0 ? 1.15 : 1/1.15;
  zoomLevel = Math.max(0.2, Math.min(20, zoomLevel * factor));
  // Zoom toward cursor
  const ratio = zoomLevel / oldZoom;
  const { s, ox, oy } = fpScale(W, H);
  panX = mx - ratio * (mx - panX - (W - FP_W * (s/zoomLevel)) / 2) - (W - FP_W * (s/zoomLevel)) / 2;
  panY = my - ratio * (my - panY - (H - FP_H * (s/zoomLevel)) / 2) - (H - FP_H * (s/zoomLevel)) / 2;
  document.getElementById('zoomLabel').textContent = zoomLevel.toFixed(1) + 'x';
  draw();
}, { passive: false });

// ── Pan (left-click drag on canvas) ──────────────────────────────────────────
canvas.addEventListener('mousedown', (ev) => {
  isPanning = true;
  panStartX = ev.clientX; panStartY = ev.clientY;
  panStartPanX = panX; panStartPanY = panY;
  canvas.style.cursor = 'grabbing';
});
canvas.addEventListener('mousemove', (ev) => {
  if (!isPanning) return;
  panX = panStartPanX + (ev.clientX - panStartX);
  panY = panStartPanY + (ev.clientY - panStartY);
  draw();
});
window.addEventListener('mouseup', () => {
  if (isPanning) { isPanning = false; canvas.style.cursor = 'crosshair'; }
});

// ── SNR Mini Heatmap ──────────────────────────────────────────────────────────
const snrMini    = document.getElementById('snrMiniCanvas');
const snrMiniCtx = snrMini.getContext('2d');
let snrImageData = null;

function renderMiniHeatmap(hoverTi, hoverRi) {
  const N = NUM_BEAMS;
  if (!snrImageData) {
    snrMini.width = N; snrMini.height = N;
    snrImageData = snrMiniCtx.createImageData(N, N);
    const d = snrImageData.data;
    for (let ti = 0; ti < N; ti++) {
      for (let ri = 0; ri < N; ri++) {
        const snr = SNR_DATA[ti * N + ri];
        const idx = (ti * N + ri) * 4;
        if (snr === null || snr === undefined) { d[idx+3] = 0; continue; }
        const [r,g,b] = snrToRgb(snr);
        d[idx]=r; d[idx+1]=g; d[idx+2]=b; d[idx+3]=255;
      }
    }
  }
  snrMiniCtx.putImageData(snrImageData, 0, 0);

  const ti = hoverTi !== undefined ? hoverTi : EXPERIMENT.bestTxIdx;
  const ri = hoverRi !== undefined ? hoverRi : EXPERIMENT.bestRxIdx;

  // Crosshair
  snrMiniCtx.save();
  snrMiniCtx.strokeStyle = 'rgba(255,255,255,0.7)';
  snrMiniCtx.lineWidth = 0.5;
  snrMiniCtx.setLineDash([2, 2]);
  snrMiniCtx.beginPath(); snrMiniCtx.moveTo(ri+0.5, 0); snrMiniCtx.lineTo(ri+0.5, N); snrMiniCtx.stroke();
  snrMiniCtx.beginPath(); snrMiniCtx.moveTo(0, ti+0.5); snrMiniCtx.lineTo(N, ti+0.5); snrMiniCtx.stroke();
  snrMiniCtx.setLineDash([]);
  snrMiniCtx.fillStyle = 'white';
  snrMiniCtx.beginPath(); snrMiniCtx.arc(ri+0.5, ti+0.5, 1.5, 0, Math.PI*2); snrMiniCtx.fill();
  snrMiniCtx.restore();

  // Update text readout
  const snr = SNR_DATA[ti * N + ri];
  document.getElementById('snrAngles').textContent =
    `TX ${TX_ANGLES[ti].toFixed(1)}° / RX ${RX_ANGLES[ri].toFixed(1)}°`;
  const box = document.getElementById('snrValueBox');
  if (snr !== null && snr !== undefined) {
    const [r,g,b] = snrToRgb(snr);
    box.textContent = snr.toFixed(2) + ' dB';
    box.style.color = `rgb(${r},${g},${b})`;
    box.style.borderColor = `rgba(${r},${g},${b},0.4)`;
  } else {
    box.textContent = 'N/A'; box.style.color = '#aaa';
  }
}

snrMini.addEventListener('mousemove', (ev) => {
  const rect = snrMini.getBoundingClientRect();
  const N = NUM_BEAMS;
  const ri = Math.min(N-1, Math.max(0, Math.floor((ev.clientX - rect.left) / rect.width  * N)));
  const ti = Math.min(N-1, Math.max(0, Math.floor((ev.clientY - rect.top)  / rect.height * N)));
  currentTi = ti; currentRi = ri;
  renderMiniHeatmap(ti, ri);
  draw();
});
snrMini.addEventListener('mouseleave', () => {
  currentTi = null; currentRi = null;
  renderMiniHeatmap();
  draw();
});

// ── Beam length slider ────────────────────────────────────────────────────────
document.getElementById('beamLenSlider').addEventListener('input', (ev) => {
  beamLenScale = parseFloat(ev.target.value);
  document.getElementById('beamLenLabel').textContent = beamLenScale.toFixed(2) + '×';
  draw();
});

// ── Init (DOMContentLoaded) ───────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  // Viridis gradient for colorbar
  const stops = VIRIDIS.map(([r,g,b]) => `rgb(${r},${g},${b})`);
  document.getElementById('snrCbarGrad').style.background =
    `linear-gradient(to right,${stops.join(',')})`;

  // Experiment info block
  const [expDate, expTime] = EXPERIMENT.timestamp.split(' ');
  document.getElementById('expName').textContent = EXPERIMENT.name;
  document.getElementById('expDate').textContent = expDate;
  document.getElementById('expTime').textContent = expTime;
  const snrEl = document.getElementById('expBestSnr');
  snrEl.textContent = EXPERIMENT.bestSnr + ' dB';
  const [sr,sg,sb] = snrToRgb(EXPERIMENT.bestSnr);
  snrEl.style.color = `rgb(${sr},${sg},${sb})`;
  document.getElementById('expBeamPair').textContent =
    `TX ${EXPERIMENT.bestTxAngle}°  /  RX ${EXPERIMENT.bestRxAngle}°`;

  document.getElementById('txBestVal').textContent = EXPERIMENT.bestTxAngle + '°';
  document.getElementById('rxBestVal').textContent = EXPERIMENT.bestRxAngle + '°';

  // SNR best info
  document.getElementById('snrBestInfo').textContent =
    `TX=${EXPERIMENT.bestTxAngle}°  RX=${EXPERIMENT.bestRxAngle}°  →  ${EXPERIMENT.bestSnr} dB`;

  // Bottom stat bar
  document.getElementById('statBar').textContent =
    `${EXPERIMENT.name}\n${EXPERIMENT.timestamp}`;

  // Zoom reset button
  document.getElementById('zoomResetBtn').addEventListener('click', () => {
    zoomLevel = 1.0; panX = 0; panY = 0;
    document.getElementById('zoomLabel').textContent = '1.0x';
    draw();
  });

  renderMiniHeatmap();
  resize();
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
