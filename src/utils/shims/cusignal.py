import cupy as cp
import numpy as np
from scipy import signal as scipy_signal

def firwin(numtaps, cutoff, **kwargs):
    return cp.asarray(scipy_signal.firwin(numtaps, cutoff, **kwargs))

def lfilter(b, a, x, **kwargs):
    b_gpu = cp.asarray(b)
    x_gpu = cp.asarray(x)
    return cp.convolve(x_gpu, b_gpu, mode='same')

def spectrogram(x, fs=1.0, window='hann', nperseg=256, **kwargs):
    f, t, Sxx = scipy_signal.spectrogram(cp.asnumpy(x), fs=fs, window=window, nperseg=nperseg, **kwargs)
    return cp.asarray(f), cp.asarray(t), cp.asarray(Sxx)
