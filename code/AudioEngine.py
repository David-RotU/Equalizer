from operator import eq

from PySide6.QtWidgets import QSlider
import numpy as np
import sounddevice as sd
import gui.EqWindow
from scipy.signal.windows import hann


class AudioEngine():

    playing = False
    audio_loaded=False
    instance: AudioEngine
    windowLength = 512
    step = 256      # 50 % Overlap
    overlap = windowLength - step
    # window = np.hanning(windowLength)
    window = hann(windowLength, sym=False)
    positionSlider: QSlider
    
    

    def __init__(self, eqWindow: EqWindow):
        self.eqWindow = eqWindow
        #self.gains = np.ones(self.step+1, dtype=np.float32)
        self.update_gains()
        self.norm = .75 #Todo compute 

        self.bufferL = np.zeros(self.windowLength)
        self.bufferR = np.zeros(self.windowLength)
        # self.normBuffer = np.zeros(self.windowLength)
        
        self.frame=0

        # for i in range(0, self.windowLength, self.step):
        #     end = min(i + self.windowLength, self.windowLength)
        #     self.norm[i:end] += self.window[:end - i] ** 2

        # self.norm[self.norm < 1e-12] = 1.0


    def compare_energy(self):
        if not self.audio_loaded:
            return
        
        self.gains = np.ones(self.windowLength // 2 + 1)
        reconstructed = self.reverse_stft()
        energyOriginal = self.compute_energy(self.sig)
        energyRecons = self.compute_energy(reconstructed)
        print("Energy Orginal:", energyOriginal)
        print("Energy Reconstructed:", energyRecons)
        print()

        print("RMS Orginal:", np.sqrt(np.mean(np.pow(self.sig, 2))))
        print("RMS Reconstructed:", np.sqrt(np.mean(np.pow(reconstructed, 2))))
        
        print()

        difference = self.sig_padded - reconstructed[:len(self.sig_padded)]
        print("Max Difference:", np.max(np.abs(difference)))
        print("Mean Difference:", np.sqrt(np.mean(np.pow(difference, 2))))
        

    def compute_energy(self, signal):
        sqared = np.pow(signal, 2)
        return np.sum(sqared)

    def reverse_stft(self):
        self.frame = 0
        self.bufferL = np.zeros(self.windowLength)
        self.bufferR = np.zeros(self.windowLength)
        
        reconstructed = []
        nxt = self.next_block()
        
        while not nxt is None:
            reconstructed.append(nxt)
            nxt = self.next_block()

        return np.concatenate(reconstructed, axis=0)

    def load_audio(self, sig, sr):
        self.audio_loaded=True
        self.sig = sig

        pad = self.step

        self.sig_padded = np.pad(
        	sig,
        	((pad, pad), (0, 0)),
	        mode="constant"
        )

        self.ZxxL = self.stdtft(self.sig_padded[:, 0])
        self.ZxxR = self.stdtft(self.sig_padded[:, 1])

        self.sample_rate = sr

        self.overlapL = np.zeros(self.windowLength - self.step)
        self.overlapR = np.zeros(self.windowLength - self.step)        
        self.stream = None

    def update_gains(self):
        num_bins = self.windowLength//2 + 1

        self.gains = np.empty(num_bins, dtype=np.float32)

        for i in range(num_bins):
            f = i / (num_bins - 1)
            self.gains[i] = self.eqWindow.interpolate(f)*2
            

    def play_audio(self, pos=0.0):
        self.stop()
        self.frame = int(pos * self.ZxxL.shape[1])

        self.overlapL[:] = 0
        self.overlapR[:] = 0

        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=2,
            blocksize=self.step,
            callback=self.callback
        )
        self.playing = True
        self.stream.start()


    def stop(self):
        self.playing = False
        self.bufferL = np.zeros(self.windowLength)
        self.bufferR = np.zeros(self.windowLength)
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def stdtft(self, sig):
        length = len(sig)

        numWindows = int(np.ceil((length - self.windowLength) / self.step)) + 1

        # Pad last window  
        padLength = (numWindows - 1) * self.step + self.windowLength - length
        sig = np.pad(sig, (0, padLength))

        Zxx = np.zeros((self.windowLength // 2 + 1, numWindows), dtype=np.complex64)

        for i in range(numWindows):
            start = i * self.step
            end = start + self.windowLength
            segment = sig[start:end] * self.window
            Zxx[:, i] = np.fft.rfft(segment)

        return Zxx

    



    def callback(self, outdata, frames, time, status):
        if self.frame < self.ZxxL.shape[1]:
            self.eqWindow.update_frequencies(self.ZxxL[:, self.frame] * self.gains)

            if not self.positionSlider.isSliderDown():
                self.positionSlider.setValue(int(self.frame / self.ZxxL.shape[1] * 100))

            
        block = self.next_block()

        if block is None:
            outdata[:] = 0
            playing = False
            self.frame = 0
            self.positionSlider.setValue(0)
            raise sd.CallbackStop()
        outdata[:] = block




    def next_block(self):       
        if self.frame >= self.ZxxL.shape[1]:
            if len(self.bufferL) < 256 or len(self.bufferR) < 256 :
                return None
            
            else:
                hop = np.column_stack((self.bufferL[:256], self.bufferR[:256]))
                self.bufferL = self.bufferL[256:]
                self.bufferR = self.bufferR[256:]

                return hop


        # Apply equalizer
        specL = self.ZxxL[:, self.frame] * self.gains
        specR = self.ZxxR[:, self.frame] * self.gains

        # Back to time domain
        winL = np.fft.irfft(specL, self.windowLength)
        winR = np.fft.irfft(specR, self.windowLength)


        # add into synthesis buffer
        self.bufferL += winL
        self.bufferR += winR     

        # output first hop
        outL = self.bufferL[:self.step].copy()# /  self.normBuffer[:self.step]
        outR = self.bufferR[:self.step].copy()# /  self.normBuffer[:self.step]



        # shift buffers
        self.bufferL[:-self.step] = self.bufferL[self.step:]
        self.bufferR[:-self.step] = self.bufferR[self.step:]        
        self.bufferL[-self.step:] = 0
        self.bufferR[-self.step:] = 0
        self.frame += 1     

        return np.column_stack((outL, outR))




instance: AudioEngine

