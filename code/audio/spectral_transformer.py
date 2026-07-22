import os
import numpy as np
import soundfile as sf
from .stft import stft, istft
from .eq_curve import EqCurve

class Spectrum:
    """
    Data container holding complex spectral representation (STFT coefficients)
    and metadata required for exact signal reconstruction.
    """
    def __init__(self, data: np.ndarray, sample_rate: int, window_length: int, hop_length: int, fft_length: int, original_length: int, window_type: str, num_channels: int):
        self.data = data  # Shape: (freq_bins, num_frames) or (freq_bins, num_frames, channels)
        self.sample_rate = sample_rate
        self.window_length = window_length
        self.hop_length = hop_length
        self.fft_length = fft_length
        self.original_length = original_length
        self.window_type = window_type
        self.num_channels = num_channels

class SpectralTransformer:
    """
    High-level API to analyze audio into the frequency domain, apply spectral equalization,
    and synthesize time-domain signals back with exact overlap-add reconstruction matching.
    """
    def __init__(self, baseFrequency: float = None, windowLength = None, hopLength = None, sampleRate: int = None, windowType: str = 'hann'):
        """
        Parameters:
            baseFrequency (float, optional): Target frequency resolution (bin spacing) in Hz.
            windowLength (float or int, optional): Window duration in seconds (if float) or samples (if int).
            hopLength (float or int, optional): Hop duration in seconds (if float) or samples (if int).
            sampleRate (int, optional): Default sample rate to assume if not provided in audio source.
            windowType (str): Type of analysis window ('hann', 'hamming', 'rectangular').
        """
        self.baseFrequency = baseFrequency
        self.windowLength = windowLength
        self.hopLength = hopLength
        self.sampleRate = sampleRate
        self.windowType = windowType

    def analyze(self, audio_source) -> Spectrum:
        """
        Performs Short-Time Fourier Transform (STFT) analysis on the audio source.
        
        Parameters:
            audio_source (str or tuple or np.ndarray):
                - File Path / Str: Path to an audio file (wav, mp3, flac).
                - Tuple: (signal_array, sample_rate)
                - np.ndarray: Raw signal array (uses default sample rate).
                
        Returns:
            Spectrum: The spectral representation of the audio signal.
        """
        if isinstance(audio_source, (str, bytes, os.PathLike)):
            sig, sr = sf.read(audio_source)
        elif isinstance(audio_source, (tuple, list)) and len(audio_source) == 2:
            sig, sr = audio_source
        elif isinstance(audio_source, np.ndarray):
            sig = audio_source
            sr = self.sampleRate if self.sampleRate is not None else 44100
        else:
            raise TypeError("Unsupported audio source type. Must be file path, (signal, sample_rate) tuple, or numpy array.")

        # Ensure signal is floating-point
        if not np.issubdtype(sig.dtype, np.floating):
            sig = sig.astype(np.float32)

        # Resolve window length in samples
        if self.windowLength is None:
            n_win = 512
        elif isinstance(self.windowLength, float):
            n_win = int(self.windowLength * sr)
        else:
            n_win = int(self.windowLength)

        # Resolve FFT length in samples
        if self.baseFrequency is not None:
            target_n_fft = int(sr / self.baseFrequency)
            n_fft = 1 << max(n_win, target_n_fft - 1).bit_length()
        else:
            n_fft = 1 << (n_win - 1).bit_length()

        # Resolve hop length in samples
        if self.hopLength is None:
            n_hop = n_win // 2
        elif isinstance(self.hopLength, float):
            n_hop = int(self.hopLength * sr)
        else:
            n_hop = int(self.hopLength)

        n_hop = min(n_hop, n_win)
        
        original_length = sig.shape[0]
        num_channels = sig.shape[1] if sig.ndim == 2 else 1

        # Perform STFT analysis
        data = stft(
            sig=sig,
            window_length=n_win,
            hop_length=n_hop,
            window_type=self.windowType,
            fft_length=n_fft
        )

        return Spectrum(
            data=data,
            sample_rate=sr,
            window_length=n_win,
            hop_length=n_hop,
            fft_length=n_fft,
            original_length=original_length,
            window_type=self.windowType,
            num_channels=num_channels
        )

    def apply_equalizer(self, spectrum: Spectrum, eq_curve_or_gains) -> Spectrum:
        """
        Applies frequency domain equalization to a Spectrum object.
        
        Parameters:
            spectrum (Spectrum): Target spectrum instance to equalize.
            eq_curve_or_gains (EqCurve or np.ndarray): Equalizer curve instance or pre-computed gain array.
            
        Returns:
            Spectrum: Modified spectrum instance with equalized STFT coefficients.
        """
        num_bins = spectrum.fft_length // 2 + 1
        if isinstance(eq_curve_or_gains, EqCurve):
            gains = eq_curve_or_gains.evaluate_gains(num_bins, spectrum.sample_rate)
        else:
            gains = np.asarray(eq_curve_or_gains)

        # Broadcast gains across time frames and channels
        if spectrum.data.ndim == 3:
            gains_expanded = gains[:, np.newaxis, np.newaxis]
        else:
            gains_expanded = gains[:, np.newaxis]

        spectrum.data = spectrum.data * gains_expanded
        return spectrum

    def synthesize(self, spectrum: Spectrum, output_path: str = None):
        """
        Reconstructs the time-domain audio signal from its spectral representation using ISTFT.
        
        Parameters:
            spectrum (Spectrum): The spectral representation object.
            output_path (str, optional): Optional file path to write reconstructed WAV file.
            
        Returns:
            np.ndarray or str: Reconstructed signal array, or output file path if output_path was provided.
        """
        recon = istft(
            stft_matrix=spectrum.data,
            window_length=spectrum.window_length,
            hop_length=spectrum.hop_length,
            fft_length=spectrum.fft_length,
            window_type=spectrum.window_type,
            original_length=spectrum.original_length
        )

        if output_path is not None:
            sf.write(output_path, recon, spectrum.sample_rate)
            return output_path

        return recon
