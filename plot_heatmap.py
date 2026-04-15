# =============================================================================
# plot_heatmap.py — Static heatmap generator for mmWave beam-sweep data
# =============================================================================
#
# Produces four types of publication-quality plots from one experiment folder:
#
#   1. Raw power heatmap      — Rx power (dBm) vs TX × RX beam index
#                               Requires raw .dat IQ files (tx_beam_0.dat, ...)
#                               If .dat files are absent, this plot is filled with NaN.
#
#   2. SNR heatmap            — SNR (dB) vs TX × RX beam index
#                               Requires snr_data.csv  ← always available
#
#   3. Incident-angle heatmap — Rx power vs (TX incident angle × RX beam angle)
#                               Incident angle = tx_boresight_deg − tx_beam_angle
#                               Requires raw .dat files
#
#   4. Incident-SNR heatmap   — SNR vs (TX incident angle × RX beam angle)
#                               Requires snr_data.csv  ← always available
#
# All plots are saved as both PNG (500 dpi) and SVG inside the experiment folder.
#
# HOW TO CUSTOMISE:
#   - NUM_BEAMS: change if your phased array has a different beam count (default 63)
#   - beam_angles / rx_beam_angles: update if your antenna uses different angles
#   - vmin/vmax on heatmaps: adjust the colour scale range to match your SNR range
#   - cmap: swap 'viridis' for any matplotlib colormap (e.g. 'plasma', 'inferno')
#   - figsize: change (20,10) to resize the output images
#   - dpi: change 500 to a lower value (e.g. 150) for faster saves during testing
#
# © 2025 Apala Pramanik · Concept: Dr. Mehmet C. Vuran · Built with Claude (Anthropic)
# =============================================================================

import numpy as np
import seaborn as sns       # type: ignore  (seaborn is not always type-checked)
import matplotlib.pyplot as plt
import pandas as pd         # type: ignore
from matplotlib.patches import Rectangle
import os
from datetime import datetime


# =============================================================================
# SECTION 1 — POWER METRIC HELPER
# =============================================================================

def calculate_power_metrics(data_array):
    """
    Compute received power metrics from a block of complex IQ samples.

    Assumes a 50-ohm system with a 1 mW (0 dBm) reference, which is standard
    for RF power measurements.

    Parameters
    ----------
    data_array : np.ndarray of np.complex64
        One block of IQ samples for a single TX/RX beam pair.
        Shape: (samples_per_beam,)

    Returns
    -------
    IQ_power_dBm : np.ndarray
        Instantaneous power in dBm for every sample in the block.
    avg_power_dBm : float
        Mean power across all samples, in dBm.
    max_power_dBm : float
        Peak power across all samples, in dBm.

    Formula
    -------
    power_linear = |IQ|²  (magnitude squared of complex sample)
    power_dBm    = 10 * log10(power_linear / 1e-3)

    NOTE: np.maximum(..., 1e-30) guards against log(0) for zero-power samples.
    """
    # Instantaneous power per sample: magnitude squared of the complex IQ value
    power_linear = np.abs(data_array) ** 2

    avg_power_linear = np.mean(power_linear)
    max_power_linear = np.max(power_linear)

    # Convert to dBm; clamp to 1e-30 to avoid -inf from log(0)
    IQ_power_dBm  = 10 * np.log10(np.maximum(power_linear,  1e-30) / 1e-3)
    avg_power_dBm = 10 * np.log10(max(avg_power_linear, 1e-30) / 1e-3)
    max_power_dBm = 10 * np.log10(max(max_power_linear, 1e-30) / 1e-3)

    return IQ_power_dBm, avg_power_dBm, max_power_dBm


# =============================================================================
# SECTION 2 — MAIN HEATMAP FUNCTION
# =============================================================================

def plotheatmap(sweep_directory_path, samples_per_beam, tx_boresight_deg=0):
    """
    Generate all heatmap plots for one beam-sweep experiment.

    Parameters
    ----------
    sweep_directory_path : str
        Path to the experiment folder. Must contain snr_data.csv.
        May optionally contain tx_beam_0.dat … tx_beam_62.dat for power plots.

    samples_per_beam : int
        Number of IQ samples recorded per TX/RX beam pair in the .dat files.
        Typically 2000. Only used when reading raw .dat files.
        Has no effect on SNR-only plots (snr_data.csv).

    tx_boresight_deg : float, optional
        The TX antenna's physical boresight direction in degrees.
        0° = TX faces perpendicular to the wall (broadside).
        Positive = TX rotated clockwise (to the right).
        This shifts the Y-axis of the incident-angle heatmaps.
        Default: 0

    Outputs (saved inside sweep_directory_path)
    -------------------------------------------
    <folder>_heatmap.png/svg              — Raw Rx power (requires .dat files)
    <folder>_snr_heatmap.png/svg          — SNR from snr_data.csv
    <folder>_incident_heatmap.png/svg     — Incident-angle power (requires .dat files)
    <folder>_incident_snr_heatmap.png/svg — Incident-angle SNR from snr_data.csv
    max_signal_powers_RFM06010.csv        — Power matrix exported as CSV
    """

    # ── Output file paths ────────────────────────────────────────────────────
    # Use the folder name as the base filename for all outputs
    folder_name = os.path.basename(os.path.normpath(sweep_directory_path))
    plot_filename     = os.path.join(sweep_directory_path, f"{folder_name}_heatmap.png")
    plot_filename_svg = os.path.join(sweep_directory_path, f"{folder_name}_heatmap.svg")

    # ── Beam geometry ────────────────────────────────────────────────────────
    # HOW TO CUSTOMISE: If your phased array has a different number of beams
    # or different angle steps, update num_beams and both angle lists here.
    # Both lists must have exactly num_beams entries.

    num_beams = 63  # Total number of beam directions per antenna (TX and RX)

    # RX beam angles: –45° to +45° in ~1.5° steps (index 0 = leftmost beam)
    rx_beam_angles = [
        -45.0, -43.5, -42.1, -40.6, -39.2, -37.7, -36.3, -34.8, -33.4, -31.9,
        -30.5, -29.0, -27.6, -26.1, -24.7, -23.2, -21.8, -20.3, -18.9, -17.4,
        -16.0, -14.5, -13.1, -11.6, -10.2,  -8.7,  -7.3,  -5.8,  -4.4,  -2.9,
         -1.5,   0.0,   1.5,   2.9,   4.4,   5.8,   7.3,   8.7,  10.2,  11.6,
         13.1,  14.5,  16.0,  17.4,  18.9,  20.3,  21.8,  23.2,  24.7,  26.1,
         27.6,  29.0,  30.5,  31.9,  33.4,  34.8,  36.3,  37.7,  39.2,  40.6,
         42.1,  43.5,  45.0
    ]

    # TX beam angles: +45° to –45° (reversed — index 0 = rightmost beam)
    # The reversed order is how the hardware sweeps TX beams
    beam_angles = [
         45.0,  43.5,  42.1,  40.6,  39.2,  37.7,  36.3,  34.8,  33.4,  31.9,
         30.5,  29.0,  27.6,  26.1,  24.7,  23.2,  21.8,  20.3,  18.9,  17.4,
         16.0,  14.5,  13.1,  11.6,  10.2,   8.7,   7.3,   5.8,   4.4,   2.9,
          1.5,   0.0,  -1.5,  -2.9,  -4.4,  -5.8,  -7.3,  -8.7, -10.2, -11.6,
        -13.1, -14.5, -16.0, -17.4, -18.9, -20.3, -21.8, -23.2, -24.7, -26.1,
        -27.6, -29.0, -30.5, -31.9, -33.4, -34.8, -36.3, -37.7, -39.2, -40.6,
        -42.1, -43.5, -45.0
    ]

    # ── Power matrix initialisation ──────────────────────────────────────────
    # All three matrices are (num_beams × num_beams).
    # Rows = TX beam index, columns = RX beam index.
    # Pre-fill with –100 dBm as a "no data" sentinel (will show as floor on plots).
    signal_strength    = np.full((num_beams, num_beams), -100, dtype=float)  # mean IQ magnitude
    avg_signal_powers  = np.full((num_beams, num_beams), -100, dtype=float)  # average power (dBm)
    max_signal_powers  = np.full((num_beams, num_beams), -100, dtype=float)  # peak power (dBm)

    # ── Load raw IQ data from .dat files ─────────────────────────────────────
    # Each file tx_beam_<N>.dat stores the IQ samples for all 63 RX beams
    # sequentially. The file is read once per TX beam, advancing the file
    # pointer by `samples_per_beam` complex64 values for each RX beam.
    #
    # If a .dat file is missing or empty, the entire TX row is filled with NaN.
    # This is normal when only snr_data.csv is available.
    for tx_beam in range(num_beams):
        mean_strengths, avg_powers_in_dBm, max_powers_in_dBm = [], [], []
        filename = os.path.join(sweep_directory_path, "tx_beam_{}.dat".format(tx_beam))

        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'rb') as f:
                for rx_beam in range(num_beams):
                    # Read exactly `samples_per_beam` complex64 values for this RX beam
                    data_array = np.fromfile(f, dtype=np.complex64, count=samples_per_beam)

                    if data_array.size == 0:
                        # Fewer samples than expected — mark as missing
                        mean_strengths.append(np.nan)
                        avg_powers_in_dBm.append(np.nan)
                        max_powers_in_dBm.append(np.nan)
                        continue

                    # Compute power metrics from the IQ block
                    IQ_power_dBm, avg_power_dBm, max_power_dBm = calculate_power_metrics(data_array)
                    mean_strengths.append(round(np.mean(np.abs(data_array)), 4))
                    avg_powers_in_dBm.append(round(avg_power_dBm, 2))
                    max_powers_in_dBm.append(round(max_power_dBm, 2))
        else:
            # .dat file missing — fill this TX row with NaN (will appear as blank in plots)
            mean_strengths    = [np.nan] * num_beams
            avg_powers_in_dBm = [np.nan] * num_beams
            max_powers_in_dBm = [np.nan] * num_beams

        # Store results for this TX beam into the matrices
        signal_strength[tx_beam, :]   = mean_strengths
        avg_signal_powers[tx_beam, :] = avg_powers_in_dBm
        max_signal_powers[tx_beam, :] = max_powers_in_dBm

    # ── Find the best beam pair (highest Rx power) ───────────────────────────
    index_max = np.argmax(max_signal_powers)
    tx_index, rx_index = np.unravel_index(index_max, max_signal_powers.shape)

    # Center beam = TX index 31, RX index 31 (both antennas pointing straight ahead at 0°)
    center_power = max_signal_powers[31, 31]

    max_signal_power     = max_signal_powers[tx_index, rx_index]
    tx_beam_angle_max    = beam_angles[tx_index]
    rx_beam_angle_max    = rx_beam_angles[rx_index]

    print(f"Maximum signal strength of {max_signal_power} dBm ; Center power of {center_power} dBm")

    # ── Export power matrix to CSV ───────────────────────────────────────────
    # Saves the full 63×63 max-power matrix with angle labels as rows/columns.
    # HOW TO CUSTOMISE: change the output filename or choose avg_signal_powers
    # instead of max_signal_powers if you prefer average power.
    df = pd.DataFrame(max_signal_powers)
    df.index   = beam_angles      # TX angles as row labels
    df.columns = rx_beam_angles   # RX angles as column labels

    # Long-form version (useful for downstream analysis tools)
    df_melted = df.reset_index().melt(id_vars='index', var_name='Rx', value_name='Power')
    df_melted.rename(columns={'index': 'Tx'}, inplace=True)

    csv_filename = os.path.join(sweep_directory_path, "max_signal_powers_RFM06010.csv")
    df.to_csv(csv_filename, index=True)

    # ── PLOT 1: Raw power heatmap (TX angle × RX angle) ──────────────────────
    # Colour scale: –110 dBm (floor) to –75 dBm (strong signal)
    # HOW TO CUSTOMISE: change vmin/vmax to match your expected power range.
    tx_angles = beam_angles
    rx_angles = rx_beam_angles

    sns.set()  # Apply the default Seaborn style (clean grid background)
    plt.figure(figsize=(20, 10))  # HOW TO CUSTOMISE: change figure size here

    ax = sns.heatmap(
        max_signal_powers,
        cmap='viridis',       # HOW TO CUSTOMISE: swap colormap (e.g. 'plasma', 'hot')
        vmin=-75,             # HOW TO CUSTOMISE: upper bound of colour scale (dBm)
        vmax=-110,            # HOW TO CUSTOMISE: lower bound of colour scale (dBm)
        cbar_kws={'label': 'Rx Power(dBm)', 'pad': 0.02}
    )

    # Make the colorbar labels legible at publication size
    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.label.set_size(20)
    cbar.ax.tick_params(labelsize=20)

    # Tick marks every 5° from –45° to +45°
    ticks = np.arange(-45, 50, 5)   # HOW TO CUSTOMISE: change step (5) for coarser/finer ticks

    ax.set_xticks(np.linspace(0, len(rx_angles) - 1, len(ticks)))
    ax.set_yticks(np.linspace(0, len(tx_angles) - 1, len(ticks)))
    ax.set_xticklabels(ticks,        fontsize=20, rotation=45, fontweight='bold')
    ax.set_yticklabels(ticks[::-1],  fontsize=20, rotation=0,  fontweight='bold')

    plt.xlabel('Rx Beam Angle', fontsize=20, fontweight='bold')
    plt.ylabel('Tx Beam Angle', fontsize=20, fontweight='bold')
    max_signal_power = round(max_signal_power, 2)
    center_power     = round(center_power, 2)
    plt.tight_layout()

    # Save at 500 dpi for print quality; lower to 150 for faster iteration
    plt.savefig(plot_filename,     dpi=500, bbox_inches='tight')
    plt.savefig(plot_filename_svg, dpi=500, bbox_inches='tight')
    plt.show()

    # ── PLOT 2: SNR heatmap (TX angle × RX angle) ────────────────────────────
    # Reads snr_data.csv and builds a 63×63 SNR matrix, then plots it.
    # HOW TO CUSTOMISE: change vmin/vmax (5, 15) to match your SNR range.
    snr_csv = os.path.join(sweep_directory_path, "snr_data.csv")
    if os.path.exists(snr_csv):
        snr_df = pd.read_csv(snr_csv, header=None,
                             names=['sample_size', 'tx_beam', 'rx_beam', 'snr_db'])

        # Build the 63×63 SNR matrix from the flat CSV rows
        snr_matrix = np.full((num_beams, num_beams), np.nan, dtype=float)
        for _, row in snr_df.iterrows():
            tx = int(row['tx_beam'])
            rx = int(row['rx_beam'])
            if tx < num_beams and rx < num_beams:
                snr_matrix[tx, rx] = row['snr_db']

        snr_plot_filename     = os.path.join(sweep_directory_path, f"{folder_name}_snr_heatmap.png")
        snr_plot_filename_svg = os.path.join(sweep_directory_path, f"{folder_name}_snr_heatmap.svg")

        plt.figure(figsize=(20, 10))
        ax2 = sns.heatmap(
            snr_matrix,
            cmap='viridis',   # HOW TO CUSTOMISE: swap colormap
            vmin=5,           # HOW TO CUSTOMISE: minimum SNR shown on colour scale (dB)
            vmax=15,          # HOW TO CUSTOMISE: maximum SNR shown on colour scale (dB)
            cbar_kws={'label': 'SNR (dB)', 'pad': 0.02}
        )

        cbar2 = ax2.collections[0].colorbar
        cbar2.ax.yaxis.label.set_size(20)
        cbar2.ax.tick_params(labelsize=20)

        ax2.set_xticks(np.linspace(0, len(rx_beam_angles) - 1, len(ticks)))
        ax2.set_yticks(np.linspace(0, len(beam_angles) - 1,    len(ticks)))
        ax2.set_xticklabels(ticks,       fontsize=20, rotation=45, fontweight='bold')
        ax2.set_yticklabels(ticks[::-1], fontsize=20, rotation=0,  fontweight='bold')

        plt.xlabel('Rx Beam Angle', fontsize=20, fontweight='bold')
        plt.ylabel('Tx Beam Angle', fontsize=20, fontweight='bold')
        plt.tight_layout()

        plt.savefig(snr_plot_filename,     dpi=500, bbox_inches='tight')
        plt.savefig(snr_plot_filename_svg, dpi=500, bbox_inches='tight')
        print(f"SNR heatmap saved to: {snr_plot_filename}")
        plt.show()
    else:
        print(f"SNR data not found: {snr_csv}")

    # ── PLOT 3: Incident-angle power heatmap ─────────────────────────────────
    # Maps TX beam angles to physical incident angles relative to the wall normal:
    #   incident_angle = tx_boresight_deg − tx_beam_angle
    # At 0° boresight: beam index 31 (0° beam angle) → 0° incident (normal incidence).
    # At 45° boresight: that same beam steers to 45° incident angle.
    #
    # HOW TO CUSTOMISE: pass a different tx_boresight_deg to shift the Y-axis.
    incident_angles = [tx_boresight_deg - a for a in beam_angles]

    # Build DataFrame with incident angles as the row index, sort ascending
    df_incident = pd.DataFrame(max_signal_powers)
    df_incident.index   = incident_angles
    df_incident.columns = rx_beam_angles
    df_incident = df_incident.sort_index()  # ascending incident angle top-to-bottom

    incident_power = df_incident.values

    # Find and report the peak
    idx_peak = np.nanargmax(incident_power)
    peak_row, peak_col = np.unravel_index(idx_peak, incident_power.shape)
    peak_incident = df_incident.index[peak_row]
    peak_rx       = df_incident.columns[peak_col]
    peak_pwr      = incident_power[peak_row, peak_col]
    print(f"\n[Incident Heatmap] Peak Power: {peak_pwr:.2f} dBm "
          f"at incident={peak_incident:.1f} deg, Rx={peak_rx:.1f} deg")

    # Tick labels span the incident angle range in 5° steps
    incident_min   = tx_boresight_deg - 45
    incident_max   = tx_boresight_deg + 45
    incident_ticks = np.arange(incident_min, incident_max + 5, 5)

    incident_plot_filename     = os.path.join(sweep_directory_path, f"{folder_name}_incident_heatmap.png")
    incident_plot_filename_svg = os.path.join(sweep_directory_path, f"{folder_name}_incident_heatmap.svg")

    plt.figure(figsize=(20, 10))
    ax3 = sns.heatmap(
        incident_power,
        cmap='viridis',
        vmin=-110,   # HOW TO CUSTOMISE: adjust colour scale bounds
        vmax=-75,
        cbar_kws={'label': 'Rx Power (dBm)', 'pad': 0.02}
    )

    cbar3 = ax3.collections[0].colorbar
    cbar3.ax.yaxis.label.set_size(20)
    cbar3.ax.tick_params(labelsize=20)

    ax3.set_xticks(np.linspace(0, num_beams - 1, len(ticks)))
    ax3.set_yticks(np.linspace(0, num_beams - 1, len(incident_ticks)))
    ax3.set_xticklabels(ticks,            fontsize=20, rotation=45, fontweight='bold')
    ax3.set_yticklabels(incident_ticks[::-1], fontsize=20, rotation=0, fontweight='bold')

    plt.xlabel('Rx Beam Angle (deg)', fontsize=20, fontweight='bold')
    plt.ylabel(f'Incident Angle (deg) [Boresight={tx_boresight_deg} deg]',
               fontsize=20, fontweight='bold')
    plt.tight_layout()

    plt.savefig(incident_plot_filename,     dpi=500, bbox_inches='tight')
    plt.savefig(incident_plot_filename_svg, dpi=500, bbox_inches='tight')
    print(f"Incident angle heatmap saved to: {incident_plot_filename}")
    plt.show()

    # ── PLOT 4: Incident-angle SNR heatmap ───────────────────────────────────
    # Same incident-angle transformation as Plot 3, but using SNR values
    # from snr_data.csv instead of raw Rx power. This is the most informative
    # plot when .dat files are not available.
    if os.path.exists(snr_csv):
        # snr_matrix may already be built above (Plot 2); rebuild only if needed
        try:
            snr_matrix
        except NameError:
            snr_df = pd.read_csv(snr_csv, header=None,
                                 names=['sample_size', 'tx_beam', 'rx_beam', 'snr_db'])
            snr_matrix = np.full((num_beams, num_beams), np.nan, dtype=float)
            for _, row in snr_df.iterrows():
                tx = int(row['tx_beam'])
                rx = int(row['rx_beam'])
                if tx < num_beams and rx < num_beams:
                    snr_matrix[tx, rx] = row['snr_db']

        # Apply the same incident-angle transformation to the SNR matrix
        df_incident_snr = pd.DataFrame(snr_matrix)
        df_incident_snr.index   = incident_angles
        df_incident_snr.columns = rx_beam_angles
        df_incident_snr = df_incident_snr.sort_index()

        incident_snr = df_incident_snr.values

        # Report peak SNR in incident-angle space
        idx_peak_snr = np.nanargmax(incident_snr)
        peak_row_snr, peak_col_snr = np.unravel_index(idx_peak_snr, incident_snr.shape)
        peak_incident_snr = df_incident_snr.index[peak_row_snr]
        peak_rx_snr       = df_incident_snr.columns[peak_col_snr]
        peak_snr_val      = incident_snr[peak_row_snr, peak_col_snr]
        print(f"\n[Incident SNR Heatmap] Peak SNR: {peak_snr_val:.2f} dB "
              f"at incident={peak_incident_snr:.1f} deg, Rx={peak_rx_snr:.1f} deg")

        incident_snr_plot     = os.path.join(sweep_directory_path, f"{folder_name}_incident_snr_heatmap.png")
        incident_snr_plot_svg = os.path.join(sweep_directory_path, f"{folder_name}_incident_snr_heatmap.svg")

        plt.figure(figsize=(20, 10))
        ax4 = sns.heatmap(
            incident_snr,
            cmap='viridis',
            vmin=5,    # HOW TO CUSTOMISE: minimum SNR on colour scale (dB)
            vmax=15,   # HOW TO CUSTOMISE: maximum SNR on colour scale (dB)
            cbar_kws={'label': 'SNR (dB)', 'pad': 0.02}
        )

        cbar4 = ax4.collections[0].colorbar
        cbar4.ax.yaxis.label.set_size(20)
        cbar4.ax.tick_params(labelsize=20)

        ax4.set_xticks(np.linspace(0, num_beams - 1, len(ticks)))
        ax4.set_yticks(np.linspace(0, num_beams - 1, len(incident_ticks)))
        ax4.set_xticklabels(ticks,                fontsize=20, rotation=45, fontweight='bold')
        ax4.set_yticklabels(incident_ticks[::-1], fontsize=20, rotation=0,  fontweight='bold')

        plt.xlabel('Rx Beam Angle (deg)', fontsize=20, fontweight='bold')
        plt.ylabel(f'Incident Angle (deg) [Boresight={tx_boresight_deg} deg]',
                   fontsize=20, fontweight='bold')
        plt.tight_layout()

        plt.savefig(incident_snr_plot,     dpi=500, bbox_inches='tight')
        plt.savefig(incident_snr_plot_svg, dpi=500, bbox_inches='tight')
        print(f"Incident SNR heatmap saved to: {incident_snr_plot}")
        plt.show()
    else:
        print(f"SNR data not found for incident SNR heatmap: {snr_csv}")


# =============================================================================
# SECTION 3 — LIVE HEATMAP PLOTTER (for real-time sweep monitoring)
# =============================================================================

class LiveHeatmapPlotter:
    """
    Real-time interactive heatmap for monitoring an ongoing beam sweep.

    Use this class when your measurement system is actively collecting data
    and you want to watch the heatmap fill in live rather than waiting until
    the sweep is complete.

    IMPORTANT: Must be created and updated from the main thread only.
    Matplotlib's interactive mode (plt.ion()) requires the main thread.

    Usage example
    -------------
    plotter = LiveHeatmapPlotter(experiment_dir="/path/to/experiment")

    # Inside your sweep loop:
    for tx_beam in range(64):
        for rx_beam in range(64):
            # ... collect measurement, update power_matrix and snr_matrix ...
            pass
        # Refresh the plot after each complete TX beam row
        plotter.update(power_matrix, snr_matrix, sweep_count=1, tx_done=tx_beam+1)

    plotter.save(sweep_count=1)   # Save a PNG snapshot

    HOW TO CUSTOMISE:
        - NUM_BEAMS: change from 64 to match your array size
        - vmin/vmax on im_pwr and im_snr: adjust to your expected power/SNR range
        - figsize in __init__: change (22,9) to resize the live window
    """

    # HOW TO CUSTOMISE: change to match your phased array's beam count
    NUM_BEAMS = 64

    def __init__(self, experiment_dir):
        """
        Initialise the live plot window with two side-by-side heatmaps.

        Parameters
        ----------
        experiment_dir : str
            Path to the experiment folder (used for snapshot filenames).
        """
        self.experiment_dir = experiment_dir

        # Enable interactive mode so the window updates without blocking
        plt.ion()
        self.fig, (self.ax_pwr, self.ax_snr) = plt.subplots(1, 2, figsize=(22, 9))
        self.fig.suptitle('Live Beam Sweep — waiting for data...', fontsize=14, fontweight='bold')

        # Start with an all-NaN matrix (no data yet)
        empty = np.full((self.NUM_BEAMS, self.NUM_BEAMS), np.nan)

        # Left panel: Rx Power heatmap
        # HOW TO CUSTOMISE: change vmin/vmax to match your hardware's power range
        self.im_pwr = self.ax_pwr.imshow(
            empty, aspect='auto', cmap='viridis',
            vmin=-110, vmax=-75,    # ← adjust power colour scale bounds here
            origin='upper', interpolation='nearest'
        )
        self.cbar_pwr = self.fig.colorbar(self.im_pwr, ax=self.ax_pwr)
        self.cbar_pwr.set_label('Rx Power (dBm)', fontsize=12)
        self.ax_pwr.set_xlabel('Rx Beam Index', fontsize=12)
        self.ax_pwr.set_ylabel('Tx Beam Index', fontsize=12)
        self.ax_pwr.set_title('Rx Power', fontsize=12)
        self._set_ticks(self.ax_pwr)

        # Right panel: SNR heatmap
        # HOW TO CUSTOMISE: change vmin/vmax to match your expected SNR range
        self.im_snr = self.ax_snr.imshow(
            empty, aspect='auto', cmap='plasma',
            vmin=0, vmax=20,         # ← adjust SNR colour scale bounds here
            origin='upper', interpolation='nearest'
        )
        self.cbar_snr = self.fig.colorbar(self.im_snr, ax=self.ax_snr)
        self.cbar_snr.set_label('SNR (dB)', fontsize=12)
        self.ax_snr.set_xlabel('Rx Beam Index', fontsize=12)
        self.ax_snr.set_ylabel('Tx Beam Index', fontsize=12)
        self.ax_snr.set_title('SNR', fontsize=12)
        self._set_ticks(self.ax_snr)

        plt.tight_layout()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def _set_ticks(self, ax):
        """Place 7 evenly-spaced tick marks on both axes."""
        n = self.NUM_BEAMS
        tick_positions = np.linspace(0, n - 1, 7)
        tick_labels    = [f'{int(round(v))}' for v in np.linspace(0, n - 1, 7)]
        ax.set_xticks(tick_positions)
        ax.set_yticks(tick_positions)
        ax.set_xticklabels(tick_labels, fontsize=9)
        ax.set_yticklabels(tick_labels, fontsize=9)

    def update(self, power_matrix, snr_matrix, sweep_count, tx_done):
        """
        Refresh both heatmaps with new data. Call from the main thread only.

        Parameters
        ----------
        power_matrix : np.ndarray, shape (NUM_BEAMS, NUM_BEAMS)
            Current Rx power values in dBm. Use NaN for unmeasured cells.
        snr_matrix   : np.ndarray, shape (NUM_BEAMS, NUM_BEAMS)
            Current SNR values in dB. Use NaN for unmeasured cells.
        sweep_count  : int
            Which sweep repetition this is (for the title bar).
        tx_done      : int
            How many TX beams have been completed in the current sweep.
        """
        self.im_pwr.set_data(power_matrix)
        self.im_snr.set_data(snr_matrix)
        self.ax_pwr.set_title(
            f'Rx Power — sweep #{sweep_count}  (Tx beams done: {tx_done}/{self.NUM_BEAMS})',
            fontsize=11, fontweight='bold'
        )
        self.ax_snr.set_title(
            f'SNR — sweep #{sweep_count}  (Tx beams done: {tx_done}/{self.NUM_BEAMS})',
            fontsize=11, fontweight='bold'
        )
        # draw_idle() + flush_events() is the correct non-blocking refresh pattern
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def save(self, sweep_count):
        """
        Save a PNG snapshot of the current live plot state.

        Parameters
        ----------
        sweep_count : int
            Used in the filename: <folder>_live_sweep001.png
        """
        folder_name = os.path.basename(os.path.normpath(self.experiment_dir))
        path = os.path.join(
            self.experiment_dir,
            f'{folder_name}_live_sweep{sweep_count:03d}.png'
        )
        self.fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f'[Plot] Saved snapshot: {path}')


# =============================================================================
# SECTION 4 — STANDALONE USAGE EXAMPLES
# =============================================================================
# Uncomment and edit the lines below to run this file directly without
# going through raytrace.py.
#
# Example 1 — SNR heatmap only (no .dat files needed):
#   sweep_directory_path = "/path/to/my_experiment"
#   plotheatmap(sweep_directory_path, samples_per_beam=2000)
#
# Example 2 — With a custom TX boresight angle:
#   sweep_directory_path = "/path/to/my_experiment"
#   plotheatmap(sweep_directory_path, samples_per_beam=2000, tx_boresight_deg=45)
