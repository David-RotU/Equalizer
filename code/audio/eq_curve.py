import numpy as np

class EqCurve:
    """
    Represents an Equalizer frequency response curve and performs logarithmic interpolation.
    Control points are represented as (x, y) tuples where:
      - x: frequency coordinate mapped logarithmically in range [0.0, 1.0] (20 Hz to 20,000 Hz)
      - y: raw vertical control value in range [0.0, 1.0] (where 0.0 corresponds to +12 dB, 1.0 to -80 dB)
    """
    def __init__(self, points=None):
        if points is None:
            # Default control points
            self.points = [(0.3, 0.5), (0.3, 0.2)]
        else:
            self.points = sorted(list(points), key=lambda p: p[0])

    def interpolate(self, f: float, sample_rate: float = 44100) -> float:
        """
        Interpolates the linear gain multiplier for a given normalized frequency f in [0.0, 1.0]
        relative to the Nyquist frequency (sample_rate / 2).
        """
        if not self.points:
            return 1.0

        # Convert normalized frequency f to frequency in Hz
        freq = f * (sample_rate / 2.0)

        # Convert frequency to log-spaced representation x in [0.0, 1.0]
        F_MIN = 20.0
        F_MAX = 20000.0
        if freq <= F_MIN:
            x = 0.0
        elif freq >= F_MAX:
            x = 1.0
        else:
            x = np.log10(freq / F_MIN) / np.log10(F_MAX / F_MIN)

        # Interpolate raw y value at x using piecewise linear segments between control points
        if x <= self.points[0][0]:
            y_raw = self.points[0][1]
        elif x >= self.points[-1][0]:
            y_raw = self.points[-1][1]
        else:
            y_raw = self.points[-1][1]
            for i in range(len(self.points) - 1):
                x1, y1_raw = self.points[i]
                x2, y2_raw = self.points[i+1]
                if x1 <= x <= x2:
                    if x2 != x1:
                        t = (x - x1) / (x2 - x1)
                        y_raw = y1_raw + (y2_raw - y1_raw) * t
                    else:
                        y_raw = y1_raw
                    break

        # Convert raw y value to gain in dBFS:
        # y_raw = 0.0 -> +12 dBFS
        # y_raw = 1.0 -> -80 dBFS
        gain_db = (1.0 - y_raw) * 92.0 - 80.0

        # Convert dBFS to linear voltage amplitude multiplier
        return float(10.0 ** (gain_db / 20.0))

    def evaluate_gains(self, num_bins: int, sample_rate: float = 44100) -> np.ndarray:
        """
        Evaluates linear gain multipliers across all num_bins linearly spaced FFT frequency bins
        from 0 Hz to Nyquist.
        
        Parameters:
            num_bins (int): Number of positive frequency bins (N_fft // 2 + 1).
            sample_rate (float): Sampling frequency in Hz.
            
        Returns:
            np.ndarray: 1D array of float32 gain multipliers of length num_bins.
        """
        gains = np.empty(num_bins, dtype=np.float32)
        for i in range(num_bins):
            f = i / (num_bins - 1) if num_bins > 1 else 0.0
            gains[i] = self.interpolate(f, sample_rate)
        return gains
