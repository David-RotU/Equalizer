from __future__ import annotations
import sys
import numpy as np
import sounddevice as sd
import soundfile as sf
from audio.spectral_transformer import SpectralTransformer
from audio.eq_curve import EqCurve
from audio.fft import irfft
from audio.metrics import evaluate_reconstruction_metrics, compute_energy

class AudioEngine:

    playing = False
    audio_loaded = False
    instance: 'AudioEngine'
    windowLength = 512
    step = 256      # 50 % Overlap
    overlap = windowLength - step
    
    def __init__(self, eq_source=None):
        AudioEngine.instance = self
        self.eq_source = eq_source
        
        self.transformer = SpectralTransformer(
            windowLength=self.windowLength,
            hopLength=self.step,
            windowType='hann'
        )

        self.bufferL = np.zeros(self.windowLength)
        self.bufferR = np.zeros(self.windowLength)

        self.frame = 0
        self.sample_rate = 44100
        
        self.num_bins = self.windowLength // 2 + 1
        self.gains = np.ones(self.num_bins, dtype=np.float32)
        self.current_mag_pre = np.zeros(self.num_bins, dtype=np.float32)
        self.current_mag_post = np.zeros(self.num_bins, dtype=np.float32)
        self.waveform_max = None
        self.waveform_min = None
        self.mag_peak = 1.0
        self.db_envelope_orig = None
        self.db_envelope_recon = None
        self.loop = False
        self.sig = None
        
        # Populate gains with initial EQ curve configuration
        self.update_gains()

    def update_gains(self, eq_curve: EqCurve = None):
        """
        Updates the frequency bin gains using the provided EqCurve or existing eq_source.
        """
        num_bins = self.windowLength // 2 + 1
        if eq_curve is not None:
            self.gains = eq_curve.evaluate_gains(num_bins, self.sample_rate)
        elif self.eq_source is not None:
            if isinstance(self.eq_source, EqCurve):
                self.gains = self.eq_source.evaluate_gains(num_bins, self.sample_rate)
            elif hasattr(self.eq_source, 'interpolate'):
                self.gains = np.empty(num_bins, dtype=np.float32)
                for i in range(num_bins):
                    f = i / (num_bins - 1) if num_bins > 1 else 0.0
                    self.gains[i] = self.eq_source.interpolate(f, self.sample_rate)
        else:
            self.gains = np.ones(num_bins, dtype=np.float32)

        self.update_equalized_envelope()

    def compare_energy(self):
        if not self.audio_loaded:
            return
        
        spectrum = self.transformer.analyze((self.sig, self.sample_rate))
        reconstructed = self.transformer.synthesize(spectrum)
        
        energy_orig = compute_energy(self.sig)
        energy_recon = compute_energy(reconstructed)
        print("Energy Original:", energy_orig)
        print("Energy Reconstructed:", energy_recon)
        print()

        print("RMS Original:", np.sqrt(np.mean(self.sig ** 2)))
        print("RMS Reconstructed:", np.sqrt(np.mean(reconstructed ** 2)))
        

    def get_energy_comparison(self) -> str:
        if not self.audio_loaded:
            return "RMS Original: - | RMS Equalized: -"
        
        spectrum = self.transformer.analyze((self.sig, self.sample_rate))
        spectrum = self.transformer.apply_equalizer(spectrum, self.gains)
        reconstructed = self.transformer.synthesize(spectrum)
        
        rms_orig = np.sqrt(np.mean(self.sig ** 2))
        rms_recon = np.sqrt(np.mean(reconstructed ** 2))
        
        return f"RMS Original: {rms_orig:.4f} | RMS Equalized: {rms_recon:.4f}"
        
    def get_comparison_metrics(self) -> dict | None:
        if not self.audio_loaded:
            return None
        
        spectrum = self.transformer.analyze((self.sig, self.sample_rate))
        spectrum = self.transformer.apply_equalizer(spectrum, self.gains)
        reconstructed = self.transformer.synthesize(spectrum)
        
        return evaluate_reconstruction_metrics(self.sig, reconstructed)

    def compute_energy(self, signal):
        return compute_energy(signal)

    def load_audio(self, sig: np.ndarray, sr: int):
        self.audio_loaded = True
        
        # Ensure audio signal is stereo; duplicate if mono
        if sig.ndim == 1:
            sig = np.column_stack((sig, sig))
            
        self.sig = sig
        self.sample_rate = sr

        # Analyze using SpectralTransformer
        spectrum = self.transformer.analyze((sig, sr))
        
        # Extract left and right channel spectra
        self.ZxxL = spectrum.data[:, :, 0]
        self.ZxxR = spectrum.data[:, :, 1]

        # Compute mag_peak for normalization
        mag_pre = (np.abs(self.ZxxL) + np.abs(self.ZxxR)) / 2.0
        self.mag_peak = float(np.max(mag_pre))
        if self.mag_peak < 1e-9:
            self.mag_peak = 1.0

        self.db_envelope_orig = self.compute_db_envelope(self.sig)

        self.overlapL = np.zeros(self.windowLength - self.step)
        self.overlapR = np.zeros(self.windowLength - self.step)        
        self.stream = None

        # Generate downsampled waveform (1000 points) for visualization
        mono_sig = np.mean(self.sig, axis=1)
        num_samples = len(mono_sig)
        num_points = 1000
        block_size = max(1, num_samples // num_points)
        self.waveform_max = np.zeros(num_points, dtype=np.float32)
        self.waveform_min = np.zeros(num_points, dtype=np.float32)
        for i in range(num_points):
            start = i * block_size
            end = min(num_samples, (i + 1) * block_size)
            if start < end:
                self.waveform_max[i] = np.max(mono_sig[start:end])
                self.waveform_min[i] = np.min(mono_sig[start:end])

        self.update_gains()

    def compute_db_envelope(self, sig, num_points=1000):
        if sig is None:
            return np.zeros(num_points, dtype=np.float32)
        mono = np.mean(sig, axis=1) if sig.ndim > 1 else sig
        num_samples = len(mono)
        block_size = max(1, num_samples // num_points)
        envelope = np.zeros(num_points, dtype=np.float32)
        for i in range(num_points):
            start = i * block_size
            end = min(num_samples, (i + 1) * block_size)
            if start < end:
                block = mono[start:end]
                rms = np.sqrt(np.mean(block ** 2))
                envelope[i] = 20 * np.log10(rms + 1e-6)
        return envelope

    def update_equalized_envelope(self):
        if not self.audio_loaded:
            return
        
        spectrum = self.transformer.analyze((self.sig, self.sample_rate))
        spectrum = self.transformer.apply_equalizer(spectrum, self.gains)
        reconstructed = self.transformer.synthesize(spectrum)
        
        self.db_envelope_recon = self.compute_db_envelope(reconstructed)

    def set_gain(self, start_bin: int, end_bin: int, gain: float):
        self.gains[start_bin:end_bin] = gain

    def set_gain_hz(self, low_hz: float, high_hz: float, gain: float):
        freq_resolution = self.sample_rate / self.windowLength
        start = int(low_hz / freq_resolution)
        end = int(high_hz / freq_resolution)
        self.gains[start:end] = gain
    
    def play_audio(self, pos=None) -> bool:
        if not self.audio_loaded:
            return False
        
        target_frame = self.frame if pos is None else int(pos * self.ZxxL.shape[1])
        if target_frame >= self.ZxxL.shape[1]:
            target_frame = 0
            
        self.stop()
        self.frame = target_frame

        self.overlapL[:] = 0
        self.overlapR[:] = 0

        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                blocksize=self.step,
                callback=self.callback
            )
            self.stream.start()
            self.playing = True
            return True
        except Exception as e:
            print(f"Error starting audio stream: {e}", file=sys.stderr)
            self.stream = None
            self.playing = False
            return False

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.playing = False
        if hasattr(self, 'current_mag_pre') and self.current_mag_pre is not None:
            self.current_mag_pre.fill(0)
            self.current_mag_post.fill(0)
        self.bufferL = np.zeros(self.windowLength)
        self.bufferR = np.zeros(self.windowLength)

    def stdtft(self, sig):
        spectrum = self.transformer.analyze((sig, self.sample_rate))
        if spectrum.data.ndim == 3:
            return spectrum.data[:, :, 0]
        return spectrum.data

    def callback(self, outdata, frames, time, status):
        block = self.next_block()
        if block is None:
            outdata[:] = 0
            raise sd.CallbackStop()
        outdata[:] = block

    def next_block(self):       
        if self.frame >= self.ZxxL.shape[1]:
            if self.loop:
                self.frame = 0
                self.bufferL.fill(0)
                self.bufferR.fill(0)
            else:
                if hasattr(self, 'current_mag_pre') and self.current_mag_pre is not None:
                    self.current_mag_pre.fill(0)
                    self.current_mag_post.fill(0)
                if len(self.bufferL) < 256: 
                    self.playing = False
                    return None
                else:
                    hop = np.column_stack((self.bufferL[:256], self.bufferR[:256]))
                    self.bufferL = self.bufferL[256:]
                    self.bufferR = self.bufferR[256:]
                    return hop

        # Apply equalizer
        specL = self.ZxxL[:, self.frame] * self.gains
        specR = self.ZxxR[:, self.frame] * self.gains

        # Save magnitude spectra for visualizer
        self.current_mag_pre = (np.abs(self.ZxxL[:, self.frame]) + np.abs(self.ZxxR[:, self.frame])) / 2.0
        self.current_mag_post = (np.abs(specL) + np.abs(specR)) / 2.0

        # Synthesis via inverse real FFT
        winL = irfft(specL, self.windowLength)
        winR = irfft(specR, self.windowLength)

        # Accumulate into synthesis buffer
        self.bufferL += winL
        self.bufferR += winR        

        # Output first hop
        outL = self.bufferL[:self.step].copy()
        outR = self.bufferR[:self.step].copy()      

        # Shift buffer
        self.bufferL[:-self.step] = self.bufferL[self.step:]
        self.bufferR[:-self.step] = self.bufferR[self.step:]        
        self.bufferL[-self.step:] = 0
        self.bufferR[-self.step:] = 0       
        self.frame += 1     

        return np.column_stack((outL, outR))

    def export_audio(self, output_path: str) -> bool:
        if not self.audio_loaded:
            return False
        try:
            spectrum = self.transformer.analyze((self.sig, self.sample_rate))
            spectrum = self.transformer.apply_equalizer(spectrum, self.gains)
            reconstructed = self.transformer.synthesize(spectrum)
            
            sf.write(output_path, reconstructed, self.sample_rate)
            return True
        except Exception as e:
            print(f"Error exporting audio: {e}", file=sys.stderr)
            return False

instance: AudioEngine
