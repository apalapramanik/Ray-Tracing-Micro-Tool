# Ray Tracing Micro Tool

> A lightweight, self-contained toolkit for analyzing and visualizing millimeter-wave (mmWave) beam-sweep measurements — from raw SNR data to interactive floor-plan reports in a single command.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)

---

## Overview

Ray Tracing Micro Tool processes 63×63 TX/RX beam-sweep data from mmWave antenna experiments and produces two types of output:

| Output | Command | Description |
|--------|---------|-------------|
| **Interactive HTML Report** | `report` | Self-contained browser report with live beam selection, floor plan overlay, SNR heatmap, and specular reflection visualization |
| **Static Heatmap PNGs** | `heatmap` | Publication-quality SNR and incident-angle heatmaps saved as PNG and SVG |

### Example Report

An example experiment and its generated report are included in [`example_experiment/`](example_experiment/).  
Open [`example_experiment.html`](example_experiment/example_experiment.html) directly in a browser to see the tool in action.

---

## Requirements

- Python 3.9 or newer
- One experiment folder containing `snr_data.csv` (see format below)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/apalapramanik/Ray-Tracing-Micro-Tool.git
cd Ray-Tracing-Micro-Tool

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Generate an interactive HTML report

```bash
python raytrace.py report path/to/my_experiment/
```

The tool will:
1. Read `snr_data.csv` from the experiment folder
2. Load the floor plan (default: `nh_2ndfloor_floorplan.json`)
3. Save a self-contained `my_experiment.html` inside the experiment folder
4. Open it automatically in your browser

To specify a custom floor plan:
```bash
python raytrace.py report path/to/my_experiment/ --floorplan path/to/my_floorplan.json
```

### Generate static heatmap PNGs

```bash
python raytrace.py heatmap path/to/my_experiment/
```

With a custom TX boresight angle (degrees, default `0`):
```bash
python raytrace.py heatmap path/to/my_experiment/ --boresight 45
```

Outputs saved inside the experiment folder:
- `<name>_snr_heatmap.png/svg` — SNR heatmap (TX angle × RX angle)
- `<name>_incident_snr_heatmap.png/svg` — SNR mapped by TX incident angle

### Full help

```bash
python raytrace.py --help
python raytrace.py report  --help
python raytrace.py heatmap --help
```

---

## Input Data Format

### What is an exhaustive beam sweep?

An **exhaustive beam sweep** is a measurement procedure in which the TX (transmitter) and RX (receiver) antennas systematically step through every combination of their beam directions. Both antennas used here are phased-array mmWave radios, each capable of forming **63 discrete beams** spanning –45° to +45° in roughly 1.5° steps.

For each of the 63 TX beams, the RX cycles through all 63 of its own beams — yielding **63 × 63 = 3,969 unique TX/RX beam pair measurements**. This exhaustive approach captures the full spatial signature of the channel: which beam directions produce the strongest link, where specular reflections contribute, and how link quality degrades as either antenna steers away from the optimal direction.

The result of one complete sweep is a single `snr_data.csv` file.

---

### `snr_data.csv`

No header row. Four comma-separated columns per measurement:

```
sample_size, tx_beam_index, rx_beam_index, snr_db
2000, 0, 0, 7.094
2000, 0, 1, 7.185
2000, 0, 2, 6.831
...
2000, 62, 62, 8.103
```

| Column | Type | Description |
|--------|------|-------------|
| `sample_size` | integer | Number of IQ samples collected at this beam pair before computing SNR. Higher values give more reliable estimates. Typically 2000. |
| `tx_beam_index` | integer (0–62) | Index of the TX beam direction. Index 0 corresponds to +45° and index 62 to –45°, stepping left to right in ~1.5° increments. |
| `rx_beam_index` | integer (0–62) | Index of the RX beam direction. Index 0 corresponds to –45° and index 62 to +45°, stepping right to left in ~1.5° increments. |
| `snr_db` | float | Signal-to-Noise Ratio measured at this TX/RX beam pair, in decibels (dB). Higher values indicate a stronger, cleaner link. |

A complete sweep contains **3,969 rows** (one per TX/RX beam pair combination).

---

## Floor Plan Setup

The floor plan defines TX/RX antenna positions, boresight directions, and wall geometry.

1. Open `floorplan.html` in your browser — it is a fully visual drag-and-drop editor
2. Place TX and RX markers, draw walls
3. Click **Export** to save a `.json` file
4. Pass it to the tool with `--floorplan your_floorplan.json`

The included `nh_2ndfloor_floorplan.json` is pre-configured for the NH Building 2nd-floor lab.  
**Create a new floor plan before running experiments in a different space.**

---

## Output Structure

```
my_experiment/
├── snr_data.csv                          ← input (required)
├── my_experiment.html                    ← interactive report
├── my_experiment_snr_heatmap.png/svg     ← TX/RX angle SNR heatmap
└── my_experiment_incident_snr_heatmap.png/svg
```

---

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `snr_data.csv not found` | Verify the folder path passed to the command |
| Report opens blank | Confirm `snr_data.csv` has 3,969 rows (63×63 beam pairs) |
| Floor plan not showing | Use `--floorplan` or verify `nh_2ndfloor_floorplan.json` is present |

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgements

This tool was conceived and initiated by **Dr. Mehmet C. Vuran** (University of Nebraska–Lincoln) as part of ongoing mmWave propagation research.

Development and implementation were carried out with assistance from **[Claude](https://claude.ai)** by Anthropic.
