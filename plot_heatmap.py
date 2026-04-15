import numpy as np
import seaborn as sns # type: ignore
import matplotlib.pyplot as plt
import pandas as pd # type: ignore
from matplotlib.patches import Rectangle
import os
from datetime import datetime


def calculate_power_metrics(data_array):
    """Compute IQ power metrics from complex samples (50-ohm, 1 mW reference)."""
    power_linear = np.abs(data_array) ** 2
    avg_power_linear = np.mean(power_linear)
    max_power_linear = np.max(power_linear)
    IQ_power_dBm   = 10 * np.log10(np.maximum(power_linear,   1e-30) / 1e-3)
    avg_power_dBm  = 10 * np.log10(max(avg_power_linear, 1e-30) / 1e-3)
    max_power_dBm  = 10 * np.log10(max(max_power_linear, 1e-30) / 1e-3)
    return IQ_power_dBm, avg_power_dBm, max_power_dBm


def plotheatmap(sweep_directory_path, samples_per_beam, tx_boresight_deg=0):

    # Extract folder name to use as the plot filename
    folder_name = os.path.basename(os.path.normpath(sweep_directory_path))
    plot_filename = os.path.join(sweep_directory_path, f"{folder_name}_heatmap.png")
    plot_filename_svg = os.path.join(sweep_directory_path, f"{folder_name}_heatmap.svg")


    # Define the number of beams and samples per beam
    num_beams = 63
    
    rx_beam_angles = [-45.0, -43.5, -42.1, -40.6, -39.2, -37.7, -36.3, -34.8, -33.4, -31.9, -30.5, -29.0, -27.6, -26.1, -24.7, -23.2, -21.8, -20.3, -18.9, -17.4, -16.0, -14.5, -13.1, -11.6, -10.2, -8.7, -7.3, -5.8, -4.4, -2.9, -1.5, 0, 1.5, 2.9, 4.4, 5.8, 7.3, 8.7, 10.2, 11.6, 13.1, 14.5, 16.0, 17.4, 18.9, 20.3, 21.8, 23.2, 24.7, 26.1, 27.6, 29.0, 30.5, 31.9, 33.4, 34.8, 36.3, 37.7, 39.2, 40.6, 42.1, 43.5, 45.0]
    
    beam_angles = [45.0, 43.5, 42.1, 40.6, 39.2, 37.7, 36.3, 34.8, 33.4, 31.9, 30.5, 29.0, 27.6, 26.1, 24.7, 23.2, 21.8, 20.3, 18.9, 17.4, 16.0, 14.5, 13.1, 11.6, 10.2, 8.7, 7.3, 5.8, 4.4, 2.9, 1.5, 0, -1.5, -2.9, -4.4, -5.8, -7.3, -8.7, -10.2, -11.6, -13.1, -14.5, -16.0, -17.4, -18.9, -20.3, -21.8, -23.2, -24.7, -26.1, -27.6, -29.0, -30.5, -31.9, -33.4, -34.8, -36.3, -37.7, -39.2, -40.6, -42.1,-43.5, -45.0]

    # Initialize arrays to store the signal strength and power
    signal_strength = np.full((num_beams, num_beams), -100, dtype=float) 
    avg_signal_powers = np.full((num_beams, num_beams), -100, dtype=float) 
    max_signal_powers = np.full((num_beams, num_beams), -100, dtype=float) 
    
    for tx_beam in range(num_beams):
        mean_strengths, avg_powers_in_dBm, max_powers_in_dBm = [], [], []
        # filename = os.path.join(sweep_directory_path, f'tx_beam_{tx_beam}.dat')
        filename = os.path.join(sweep_directory_path, "tx_beam_{}.dat".format(tx_beam))

        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'rb') as f:
                for rx_beam in range(num_beams):
                    data_array = np.fromfile(f, dtype=np.complex64, count=samples_per_beam)
                    # print("Data array shape = ",data_array.shape)
                    if data_array.size == 0:
                        mean_strengths.append(np.nan)
                        avg_powers_in_dBm.append(np.nan)
                        max_powers_in_dBm.append(np.nan)
                        continue

                    IQ_power_dBm, avg_power_dBm, max_power_dBm = calculate_power_metrics(data_array)
                    mean_strengths.append(round(np.mean(np.abs(data_array)), 4))
                    avg_powers_in_dBm.append(round(avg_power_dBm, 2))
                    max_powers_in_dBm.append(round(max_power_dBm, 2))

        else:
            mean_strengths = [np.nan] * num_beams
            avg_powers_in_dBm = [np.nan] * num_beams
            max_powers_in_dBm = [np.nan] * num_beams

        signal_strength[tx_beam, :] = mean_strengths
        avg_signal_powers[tx_beam, :] = avg_powers_in_dBm
        max_signal_powers[tx_beam, :] = max_powers_in_dBm

    # Find the index of the maximum value in the signal_strength array
    index_max = np.argmax(max_signal_powers)

    # Convert the flat index to a 2D index (row, column)
    tx_index, rx_index = np.unravel_index(index_max, max_signal_powers.shape)

    center_power = max_signal_powers[31,31]

    # After finding the indices of the maximum value
    max_signal_power = max_signal_powers[tx_index, rx_index]

    # Extract the corresponding beam angles using the indices
    tx_beam_angle_max = beam_angles[tx_index]
    rx_beam_angle_max = rx_beam_angles[rx_index]

    print(f"Maximum signal strength of {max_signal_power} dBm ; Center power of {center_power} dBm")


    '''
    Save the recieved powers to a CSV file and plot the heatmap
    '''
    # Prepare the data
    # Create a DataFrame from the max_signal_powers array
    df = pd.DataFrame(max_signal_powers)

    # Add Tx and Rx beam angles as the index and column names
    df.index = beam_angles  # Assuming beam_angles is a list of Tx beam angles
    df.columns = rx_beam_angles  # Assuming the same angles are used for Rx

    # Optionally, if you want to "melt" the DataFrame to have a long-form DataFrame with Tx, Rx, and Power columns, you can do:
    df_melted = df.reset_index().melt(id_vars='index', var_name='Rx', value_name='Power')
    df_melted.rename(columns={'index': 'Tx'}, inplace=True)

    csv_filename = os.path.join(sweep_directory_path, "max_signal_powers_RFM06010.csv")
    # Save to CSV
    df.to_csv(csv_filename, index=True) # Save the original matrix form
    
    '''
    Plot the heatmap
    '''
    # Define the Tx and Rx beam angles
    tx_angles = beam_angles
    rx_angles = rx_beam_angles


    sns.set()  # Set the default Seaborn style
    plt.figure(figsize=(20,10))  # Adjust the figure sizes

    # Plot the heatmap with the viridis colormap
    ax = sns.heatmap(max_signal_powers, cmap='viridis', vmin=-75, vmax=-110, cbar_kws={'label': 'Rx Power(dBm)', 'pad': 0.02})


    # Increase the font size of the colorbar label
    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.label.set_size(20)

    # Increase the font size of the colorbar tick labels
    cbar.ax.tick_params(labelsize=20)  # Adjust the value as needed

    # Define the range of ticks
    ticks = np.arange(-45, 50, 5)  # Include 45

    # Set x and y ticks to show multiples of 5 from -45 to 45 for Rx and 45 to -45 for Tx, and rotate x-ticks
    ax.set_xticks(np.linspace(0, len(rx_angles) - 1, len(ticks)))
    ax.set_yticks(np.linspace(0, len(tx_angles) - 1, len(ticks)))
    ax.set_xticklabels(ticks, fontsize=20, rotation=45,fontweight='bold')
    ax.set_yticklabels(ticks[::-1], fontsize=20, rotation=0,fontweight='bold') 

  

    # Add a point where the maximum signal is located
    # ax.scatter(rx_index, tx_index, color='white', s=200, linewidth=2)

    # # Add a point at the center
    # ax.scatter(31, 31, color='yellow', s=200, linewidth=2)

    # # Add text at the (0, 0) index
    # ax.text(0.5, 0.5, "(0,0)", color='yellow', fontsize=12, ha='center', va='center')

    plt.xlabel('Rx Beam Angle', fontsize=20,fontweight='bold')
    plt.ylabel('Tx Beam Angle', fontsize=20,fontweight='bold')
    max_signal_power=round(max_signal_power,2)
    center_power = round(center_power,2)
    # plt.title(f"Maximum signal strength : {max_signal_power} dBm ; Center power :{center_power} dBm at {distance}m and {elevation}ft height ", fontsize=20, fontweight = 'bold')
    plt.tight_layout()  # To ensure everything fits nicely
   

    # Save the plot to a file
    plt.savefig(plot_filename, dpi=500, bbox_inches='tight')
    plt.savefig(plot_filename_svg, dpi=500, bbox_inches='tight')
    
    # Disable plot to let the function be used in a loop
    plt.show()

    '''
    Plot the SNR heatmap from snr_data.csv
    '''
    snr_csv = os.path.join(sweep_directory_path, "snr_data.csv")
    if os.path.exists(snr_csv):
        snr_df = pd.read_csv(snr_csv, header=None, names=['sample_size', 'tx_beam', 'rx_beam', 'snr_db'])

        # Build 63x63 SNR matrix
        snr_matrix = np.full((num_beams, num_beams), np.nan, dtype=float)
        for _, row in snr_df.iterrows():
            tx = int(row['tx_beam'])
            rx = int(row['rx_beam'])
            if tx < num_beams and rx < num_beams:
                snr_matrix[tx, rx] = row['snr_db']

        snr_plot_filename = os.path.join(sweep_directory_path, f"{folder_name}_snr_heatmap.png")
        snr_plot_filename_svg = os.path.join(sweep_directory_path, f"{folder_name}_snr_heatmap.svg")

        plt.figure(figsize=(20, 10))

        ax2 = sns.heatmap(snr_matrix, cmap='viridis', vmin=5, vmax=15, cbar_kws={'label': 'SNR (dB)', 'pad': 0.02})

        cbar2 = ax2.collections[0].colorbar
        cbar2.ax.yaxis.label.set_size(20)
        cbar2.ax.tick_params(labelsize=20)

        ax2.set_xticks(np.linspace(0, len(rx_beam_angles) - 1, len(ticks)))
        ax2.set_yticks(np.linspace(0, len(beam_angles) - 1, len(ticks)))
        ax2.set_xticklabels(ticks, fontsize=20, rotation=45, fontweight='bold')
        ax2.set_yticklabels(ticks[::-1], fontsize=20, rotation=0, fontweight='bold')

        plt.xlabel('Rx Beam Angle', fontsize=20, fontweight='bold')
        plt.ylabel('Tx Beam Angle', fontsize=20, fontweight='bold')
        plt.tight_layout()

        plt.savefig(snr_plot_filename, dpi=500, bbox_inches='tight')
        plt.savefig(snr_plot_filename_svg, dpi=500, bbox_inches='tight')

        print(f"SNR heatmap saved to: {snr_plot_filename}")
        plt.show()
    else:
        print(f"SNR data not found: {snr_csv}")

    '''
    Plot Incident Angle vs Rx Beam heatmap
    incident_angle = tx_boresight_deg - tx_beam_angle
    0 deg boresight = perpendicular to wall (normal)
    positive boresight = TX rotated to the right
    '''
    incident_angles = [tx_boresight_deg - a for a in beam_angles]

    # Build DataFrame with incident angles as rows
    df_incident = pd.DataFrame(max_signal_powers)
    df_incident.index = incident_angles
    df_incident.columns = rx_beam_angles
    df_incident = df_incident.sort_index()

    incident_power = df_incident.values

    # Peak detection
    idx_peak = np.nanargmax(incident_power)
    peak_row, peak_col = np.unravel_index(idx_peak, incident_power.shape)
    peak_incident = df_incident.index[peak_row]
    peak_rx = df_incident.columns[peak_col]
    peak_pwr = incident_power[peak_row, peak_col]
    print(f"\n[Incident Heatmap] Peak Power: {peak_pwr:.2f} dBm at incident={peak_incident:.1f} deg, Rx={peak_rx:.1f} deg")

    # Tick ranges
    incident_min = tx_boresight_deg - 45
    incident_max = tx_boresight_deg + 45
    incident_ticks = np.arange(incident_min, incident_max + 5, 5)

    incident_plot_filename = os.path.join(sweep_directory_path, f"{folder_name}_incident_heatmap.png")
    incident_plot_filename_svg = os.path.join(sweep_directory_path, f"{folder_name}_incident_heatmap.svg")

    plt.figure(figsize=(20, 10))
    ax3 = sns.heatmap(
        incident_power, cmap='viridis', vmin=-110, vmax=-75,
        cbar_kws={'label': 'Rx Power (dBm)', 'pad': 0.02}
    )

    cbar3 = ax3.collections[0].colorbar
    cbar3.ax.yaxis.label.set_size(20)
    cbar3.ax.tick_params(labelsize=20)

    ax3.set_xticks(np.linspace(0, num_beams - 1, len(ticks)))
    ax3.set_yticks(np.linspace(0, num_beams - 1, len(incident_ticks)))
    ax3.set_xticklabels(ticks, fontsize=20, rotation=45, fontweight='bold')
    ax3.set_yticklabels(incident_ticks[::-1], fontsize=20, rotation=0, fontweight='bold')

    plt.xlabel('Rx Beam Angle (deg)', fontsize=20, fontweight='bold')
    plt.ylabel(f'Incident Angle (deg) [Boresight={tx_boresight_deg} deg]', fontsize=20, fontweight='bold')
    plt.tight_layout()

    plt.savefig(incident_plot_filename, dpi=500, bbox_inches='tight')
    plt.savefig(incident_plot_filename_svg, dpi=500, bbox_inches='tight')
    print(f"Incident angle heatmap saved to: {incident_plot_filename}")
    plt.show()

    '''
    Plot Incident Angle vs Rx Beam heatmap for SNR
    Same incident angle transformation as above, but using SNR values
    '''
    if os.path.exists(snr_csv):
        # Rebuild SNR matrix if it wasn't built by the earlier SNR heatmap block
        try:
            snr_matrix
        except NameError:
            snr_df = pd.read_csv(snr_csv, header=None, names=['sample_size', 'tx_beam', 'rx_beam', 'snr_db'])
            snr_matrix = np.full((num_beams, num_beams), np.nan, dtype=float)
            for _, row in snr_df.iterrows():
                tx = int(row['tx_beam'])
                rx = int(row['rx_beam'])
                if tx < num_beams and rx < num_beams:
                    snr_matrix[tx, rx] = row['snr_db']

        # Build DataFrame with incident angles as rows
        df_incident_snr = pd.DataFrame(snr_matrix)
        df_incident_snr.index = incident_angles
        df_incident_snr.columns = rx_beam_angles
        df_incident_snr = df_incident_snr.sort_index()

        incident_snr = df_incident_snr.values

        # Peak detection
        idx_peak_snr = np.nanargmax(incident_snr)
        peak_row_snr, peak_col_snr = np.unravel_index(idx_peak_snr, incident_snr.shape)
        peak_incident_snr = df_incident_snr.index[peak_row_snr]
        peak_rx_snr = df_incident_snr.columns[peak_col_snr]
        peak_snr_val = incident_snr[peak_row_snr, peak_col_snr]
        print(f"\n[Incident SNR Heatmap] Peak SNR: {peak_snr_val:.2f} dB at incident={peak_incident_snr:.1f} deg, Rx={peak_rx_snr:.1f} deg")

        incident_snr_plot = os.path.join(sweep_directory_path, f"{folder_name}_incident_snr_heatmap.png")
        incident_snr_plot_svg = os.path.join(sweep_directory_path, f"{folder_name}_incident_snr_heatmap.svg")

        plt.figure(figsize=(20, 10))
        ax4 = sns.heatmap(
            incident_snr, cmap='viridis', vmin=5, vmax=15,
            cbar_kws={'label': 'SNR (dB)', 'pad': 0.02}
        )

        cbar4 = ax4.collections[0].colorbar
        cbar4.ax.yaxis.label.set_size(20)
        cbar4.ax.tick_params(labelsize=20)

        ax4.set_xticks(np.linspace(0, num_beams - 1, len(ticks)))
        ax4.set_yticks(np.linspace(0, num_beams - 1, len(incident_ticks)))
        ax4.set_xticklabels(ticks, fontsize=20, rotation=45, fontweight='bold')
        ax4.set_yticklabels(incident_ticks[::-1], fontsize=20, rotation=0, fontweight='bold')

        plt.xlabel('Rx Beam Angle (deg)', fontsize=20, fontweight='bold')
        plt.ylabel(f'Incident Angle (deg) [Boresight={tx_boresight_deg} deg]', fontsize=20, fontweight='bold')
        plt.tight_layout()

        plt.savefig(incident_snr_plot, dpi=500, bbox_inches='tight')
        plt.savefig(incident_snr_plot_svg, dpi=500, bbox_inches='tight')
        print(f"Incident SNR heatmap saved to: {incident_snr_plot}")
        plt.show()
    else:
        print(f"SNR data not found for incident SNR heatmap: {snr_csv}")


class LiveHeatmapPlotter:
    """
    Real-time interactive heatmap for continuous beam sweeping.

    Must be created and updated from the main thread (matplotlib requirement).
    Call update() after each beam pair measurement and the plot will refresh
    live as the sweep progresses.
    """

    NUM_BEAMS = 64

    def __init__(self, experiment_dir):
        self.experiment_dir = experiment_dir

        plt.ion()
        self.fig, (self.ax_pwr, self.ax_snr) = plt.subplots(1, 2, figsize=(22, 9))
        self.fig.suptitle('Live Beam Sweep — waiting for data...', fontsize=14, fontweight='bold')

        empty = np.full((self.NUM_BEAMS, self.NUM_BEAMS), np.nan)

        # --- Power heatmap ---
        self.im_pwr = self.ax_pwr.imshow(
            empty, aspect='auto', cmap='viridis',
            vmin=-110, vmax=-75, origin='upper', interpolation='nearest'
        )
        self.cbar_pwr = self.fig.colorbar(self.im_pwr, ax=self.ax_pwr)
        self.cbar_pwr.set_label('Rx Power (dBm)', fontsize=12)
        self.ax_pwr.set_xlabel('Rx Beam Index', fontsize=12)
        self.ax_pwr.set_ylabel('Tx Beam Index', fontsize=12)
        self.ax_pwr.set_title('Rx Power', fontsize=12)
        self._set_ticks(self.ax_pwr)

        # --- SNR heatmap ---
        self.im_snr = self.ax_snr.imshow(
            empty, aspect='auto', cmap='plasma',
            vmin=0, vmax=20, origin='upper', interpolation='nearest'
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
        n = self.NUM_BEAMS
        tick_positions = np.linspace(0, n - 1, 7)
        tick_labels = [f'{int(round(v))}' for v in np.linspace(0, n - 1, 7)]
        ax.set_xticks(tick_positions)
        ax.set_yticks(tick_positions)
        ax.set_xticklabels(tick_labels, fontsize=9)
        ax.set_yticklabels(tick_labels, fontsize=9)

    def update(self, power_matrix, snr_matrix, sweep_count, tx_done):
        """Refresh both heatmaps. Must be called from the main thread."""
        self.im_pwr.set_data(power_matrix)
        self.im_snr.set_data(snr_matrix)
        self.ax_pwr.set_title(
            f'Rx Power — sweep #{sweep_count}  (Tx beams done: {tx_done}/64)',
            fontsize=11, fontweight='bold'
        )
        self.ax_snr.set_title(
            f'SNR — sweep #{sweep_count}  (Tx beams done: {tx_done}/64)',
            fontsize=11, fontweight='bold'
        )
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def save(self, sweep_count):
        """Save a PNG snapshot of the current plot."""
        folder_name = os.path.basename(os.path.normpath(self.experiment_dir))
        path = os.path.join(
            self.experiment_dir,
            f'{folder_name}_live_sweep{sweep_count:03d}.png'
        )
        self.fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f'[Plot] Saved snapshot: {path}')


# Example Usage:

# sweep_directory_path = "/home/cse-vuran-32/fullsweep_data/wall_exp/nh_cax_feb10_gain15db_3m_t1" # linux
# # sweep_directory_path = "sweepData/test_apr3" # linux
# plotheatmap(sweep_directory_path,2000)

# sweep_directory_path = "/home/cse-vuran-32/fullsweep_data/wall_exp/nh_cax_feb4_gain3db_3m_t1" # linux
# # sweep_directory_path = "sweepData/test_apr3" # linux
# plotheatmap(sweep_directory_path,2000)