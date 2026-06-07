import numpy as np
import pandas as pd
from scipy.signal import savgol_filter, butter, filtfilt


def butter_lowpass_filter(data, cutoff_freq, sample_rate, filter_order=1):
    """Apply a lowpass Butterworth filter to the data."""
    nyquist_rate = 0.5 * sample_rate
    normalized_cutoff = cutoff_freq / nyquist_rate
    b, a = butter(filter_order, normalized_cutoff, btype='low')
    return filtfilt(b, a, data)


class PhotometryRawProcessor:
    def __init__(self, file_path=None, dataframe=None):
        self.file_path = file_path
        self.raw_data = dataframe if dataframe is not None else pd.read_csv(
            file_path)
        self.time_seconds = None
        self.signal_405 = None
        self.signal_465 = None

    def slice_data(self, time_column, signal_405_column, signal_465_column, start_time, end_time):
        """
        Load data and slice based on provided column names and time range.

        Parameters:
        - time_column (str): The name of the time column.
        - signal_405_column (str): The name of the 405nm signal column.
        - signal_465_column (str): The name of the 465nm signal column.
        - start_time (float, optional): The start time in seconds.
        - end_time (float, optional): The end time in seconds.
        """
        # Define analysis window
        start_index = int(start_time / 0.1) if start_time else 0
        end_index = int(end_time / 0.1) if end_time else len(self.time_seconds)

        if end_index <= start_index:
            raise ValueError("End time must be greater than start time.")

        # Slice data
        self.time_seconds = self.time_seconds[start_index:end_index]
        self.signal_405 = self.signal_405[start_index:end_index]
        self.signal_465 = self.signal_465[start_index:end_index]

    def load_data_to_numpy(self, time_column, signal_405_column, signal_465_column):
        """
        Load data from the raw data to numpy arrays.

        Parameters:
        - time_column (str): The name of the time column.
        - signal_405_column (str): The name of the 405nm signal column.
        - signal_465_column (str): The name of the 465nm signal column.

        Returns:
        - tuple: (time_array, signal_405_array, signal_465_array) as NumPy arrays.

        Raises:
        - ValueError: If the column names are not found in the raw data.
        """
        # Verify that the required columns exist in the DataFrame
        missing_columns = [
            col for col in [time_column, signal_405_column, signal_465_column]
            if col not in self.raw_data.columns
        ]
        if missing_columns:
            raise ValueError(f"The following columns are missing in the raw data: {
                            missing_columns}")

        # Convert the specified columns to NumPy arrays
        time_array = self.raw_data[time_column].to_numpy()
        signal_405_array = self.raw_data[signal_405_column].to_numpy()
        signal_465_array = self.raw_data[signal_465_column].to_numpy()

        return time_array, signal_405_array, signal_465_array

    def prepare_filtered_signals(self):
        """
        Prepare filtered and smoothed signals for background display.
        
        Returns:
        - dict: A dictionary containing the filtered and smoothed signals.
        """
        scale_factor = np.mean(self.signal_465) / np.mean(self.signal_405)
        scaled_signal_405 = self.signal_405 * scale_factor
        fit_scaled_405 = np.polyfit(
            range(len(scaled_signal_405)), scaled_signal_405, 2)
        fitted_scaled_405 = np.polyval(
            fit_scaled_405, range(len(scaled_signal_405)))

        raw_delta_f_405 = [
            (self.signal_405[i] - np.polyval(fit_scaled_405, i)
             ) / np.polyval(fit_scaled_405, i)
            for i in range(len(self.signal_405))
        ]
        adjusted_405 = [
            fitted_scaled_405[i] * raw_delta_f_405[i] + fitted_scaled_405[i]
            for i in range(len(self.signal_405))
        ]

        sample_rate = 10.0  # Hz
        cutoff_freq = 0.4  # Hz
        filtered_adjusted_405 = butter_lowpass_filter(
            adjusted_405, cutoff_freq, sample_rate)
        filtered_465 = butter_lowpass_filter(
            self.signal_465, cutoff_freq, sample_rate)

        processed_signals = {
            "filtered_adjusted_405": filtered_adjusted_405,
            "smooth_adjusted_405_opt1": savgol_filter(filtered_adjusted_405, 21, 3),
            "smooth_adjusted_405_opt2": savgol_filter(filtered_adjusted_405, 501, 3),
            "smooth_adjusted_405_opt3": savgol_filter(filtered_adjusted_405, 501, 0),
            "smooth_adjusted_405_opt4": savgol_filter(filtered_adjusted_405, 21, 0),
            "smooth_signal_465": savgol_filter(filtered_465, 21, 3),
        }
        
        return processed_signals

    def perform_analysis(self, analysis_option):
        """
        Perform final analysis based on the selected analysis option.
        """
        if self.processed_signals is None:
            raise ValueError(
                "Filtered signals are not prepared. Run `prepare_filtered_signals` first.")

        selected_adjusted_405 = self.processed_signals[f"smooth_adjusted_405_opt{
            analysis_option}"]
        smooth_signal_465 = self.processed_signals["smooth_signal_465"]

        dff_465 = (smooth_signal_465 - selected_adjusted_405) / \
            selected_adjusted_405
        dff_405 = (selected_adjusted_405 - np.polyfit(range(len(selected_adjusted_405)), selected_adjusted_405, 2)) / \
            np.polyfit(range(len(selected_adjusted_405)),
                       selected_adjusted_405, 2)

        z_score_465 = (dff_465 - np.mean(dff_465)) / np.std(dff_465)
        z_score_405 = (dff_405 - np.mean(dff_405)) / np.std(dff_405)

        self.final_results = {
            "time_minutes": self.time_minutes,
            "dff_465": dff_465,
            "dff_405": dff_405,
            "z_score_465": z_score_465,
            "z_score_405": z_score_405,
        }
        return self.final_results
