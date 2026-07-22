"""
Fast Fourier Transform (FFT) Implementation

This module contains a pure Python implementation of the Cooley-Tukey Radix-2
recursive Fast Fourier Transform algorithm, twiddle factor caching, and real-valued
transform wrappers (rfft, irfft, rfftfreq).
"""

import numpy as np

# Cache precomputed twiddle factors W_N^k = exp(-2j * pi * k / N)
_twiddles = {}

def get_twiddle(N: int) -> np.ndarray:
    """
    Returns precomputed twiddle factors exp(-2j * pi * k / N) for k in 0..N/2-1.
    """
    if N not in _twiddles:
        _twiddles[N] = np.exp(-2j * np.pi * np.arange(N // 2) / N)
    return _twiddles[N]

def fft(x: np.ndarray) -> np.ndarray:
    """
    Computes 1D Discrete Fourier Transform using Cooley-Tukey Radix-2 recursive algorithm.
    Input length len(x) must be a power of 2.
    """
    N = len(x)
    if N <= 4:
        if N <= 1:
            return x
        elif N == 2:
            return np.array([x[0] + x[1], x[0] - x[1]], dtype=complex)
        elif N == 4:
            e0, e1 = x[0] + x[2], x[0] - x[2]
            o0, o1 = x[1] + x[3], x[1] - x[3]
            return np.array([
                e0 + o0,
                e1 - 1j * o1,
                e0 - o0,
                e1 + 1j * o1
            ], dtype=complex)
            
    even = fft(x[0::2])
    odd = fft(x[1::2])
    T = get_twiddle(N) * odd
    return np.concatenate([even + T, even - T])

def ifft(x: np.ndarray) -> np.ndarray:
    """
    Computes 1D Inverse Discrete Fourier Transform via conjugate trick:
    ifft(x) = conj(fft(conj(x))) / N
    """
    N = len(x)
    return np.conjugate(fft(np.conjugate(x))) / N

def irfft(spec: np.ndarray, n: int) -> np.ndarray:
    """
    Inverse Real Fast Fourier Transform implemented in pure Python.
    Reconstructs n-length real-valued signal from half-spectrum of size n//2 + 1.
    Assumes n is a power of 2.
    """
    complex_dtype = np.complex128 if np.issubdtype(spec.dtype, np.complex128) else np.complex64
    full_spec = np.zeros(n, dtype=complex_dtype)
    full_spec[:n//2 + 1] = spec
    if n % 2 == 0:
        full_spec[n//2 + 1:] = np.conjugate(spec[1:n//2][::-1])
    else:
        full_spec[n//2 + 1:] = np.conjugate(spec[1:n//2 + 1][::-1])
    x_complex = ifft(full_spec)
    return np.real(x_complex)

def rfft(a: np.ndarray, n: int = None, axis: int = -1) -> np.ndarray:
    """
    Real Fast Fourier Transform implemented using custom Cooley-Tukey audio.fft.
    Computes non-redundant positive frequency spectrum bins (n // 2 + 1).
    """
    a = np.asarray(a)
    ndim = a.ndim
    if axis < 0:
        axis += ndim
    
    if axis != ndim - 1:
        a = np.moveaxis(a, axis, -1)
    
    orig_shape = a.shape
    if n is None:
        n = orig_shape[-1]
        
    flat_a = a.reshape(-1, orig_shape[-1])
    num_signals = flat_a.shape[0]
    out_len = n // 2 + 1
    
    complex_dtype = np.complex128 if np.issubdtype(a.dtype, np.float64) or np.issubdtype(a.dtype, np.complex128) else np.complex64
    out = np.empty((num_signals, out_len), dtype=complex_dtype)
    
    for i in range(num_signals):
        sig = flat_a[i]
        if len(sig) < n:
            sig = np.pad(sig, (0, n - len(sig)), mode='constant')
        elif len(sig) > n:
            sig = sig[:n]
        full_fft = fft(sig)
        out[i] = full_fft[:out_len]
        
    res_shape = list(orig_shape)
    res_shape[-1] = out_len
    out = out.reshape(res_shape)
    
    if axis != ndim - 1:
        out = np.moveaxis(out, -1, axis)
        
    return out

def rfftfreq(n: int, d: float = 1.0) -> np.ndarray:
    """
    Returns Discrete Fourier Transform sample bin frequencies for real input.
    """
    n = int(n)
    val = 1.0 / (n * d)
    N = n // 2 + 1
    return np.arange(0, N, dtype=np.float64) * val


