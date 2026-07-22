import numpy as np

def compute_energy(signal: np.ndarray) -> float:
    """
    Computes total energy (sum of squared amplitudes) of an audio signal.
    """
    return float(np.sum(signal ** 2))

def compute_rms(signal: np.ndarray) -> float:
    """
    Computes Root Mean Square (RMS) level of an audio signal.
    """
    return float(np.sqrt(np.mean(signal ** 2)))

def compute_peak(signal: np.ndarray) -> float:
    """
    Computes peak absolute amplitude of an audio signal.
    """
    return float(np.max(np.abs(signal)))

def compute_crest_factor(signal: np.ndarray) -> float:
    """
    Computes Crest Factor (Peak to RMS ratio) of an audio signal.
    """
    rms = compute_rms(signal)
    if rms > 0:
        return float(compute_peak(signal) / rms)
    return 0.0

def compute_sdr(orig: np.ndarray, recon: np.ndarray) -> float:
    """
    Computes Signal-to-Distortion Ratio (SDR) in dB between original and reconstructed signals.
    """
    noise_power = np.sum((orig - recon) ** 2)
    signal_power = np.sum(orig ** 2)
    if noise_power > 0 and signal_power > 0:
        return float(10.0 * np.log10(signal_power / noise_power))
    elif noise_power == 0:
        return float('inf')
    else:
        return -float('inf')

def evaluate_reconstruction_metrics(orig: np.ndarray, recon: np.ndarray) -> dict:
    """
    Evaluates quantitative reconstruction metrics comparing original and processed/reconstructed signals.
    
    Parameters:
        orig (np.ndarray): Original reference signal (1D mono or 2D stereo).
        recon (np.ndarray): Reconstructed or equalized signal.
        
    Returns:
        dict: Dictionary containing RMS, Energy, Peak, Crest Factor, Pearson Correlation, MSE, MAE, and SDR.
    """
    # Mix to mono for metrics calculation if multi-channel
    if orig.ndim > 1:
        orig_mono = np.mean(orig, axis=1)
    else:
        orig_mono = orig
        
    if recon.ndim > 1:
        recon_mono = np.mean(recon, axis=1)
    else:
        recon_mono = recon
        
    # Align signal lengths
    min_len = min(len(orig_mono), len(recon_mono))
    orig_mono = orig_mono[:min_len]
    recon_mono = recon_mono[:min_len]
    
    rms_orig = compute_rms(orig_mono)
    rms_recon = compute_rms(recon_mono)
    
    energy_orig = compute_energy(orig_mono)
    energy_recon = compute_energy(recon_mono)
    
    peak_orig = compute_peak(orig_mono)
    peak_recon = compute_peak(recon_mono)
    
    crest_orig = compute_crest_factor(orig_mono)
    crest_recon = compute_crest_factor(recon_mono)
    
    std_orig = np.std(orig_mono)
    std_recon = np.std(recon_mono)
    if std_orig > 0 and std_recon > 0:
        correlation = float(np.corrcoef(orig_mono, recon_mono)[0, 1])
    else:
        correlation = 0.0
        
    mse = float(np.mean((orig_mono - recon_mono) ** 2))
    mae = float(np.mean(np.abs(orig_mono - recon_mono)))
    sdr = compute_sdr(orig_mono, recon_mono)
    
    return {
        'rms_orig': rms_orig,
        'rms_recon': rms_recon,
        'energy_orig': energy_orig,
        'energy_recon': energy_recon,
        'peak_orig': peak_orig,
        'peak_recon': peak_recon,
        'crest_orig': crest_orig,
        'crest_recon': crest_recon,
        'correlation': correlation,
        'mse': mse,
        'mae': mae,
        'sdr': sdr
    }
