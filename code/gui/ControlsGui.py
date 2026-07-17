import os
from signal import signal
import sys

import gui.EqWindow
from AudioEngine import AudioEngine
from gui.ControlPoint import ControlPoint
from PySide6.QtCore import QPointF, QSize, Qt, QLineF, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QMainWindow, QPushButton, QSlider, QStyle, QWidget
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPen, QColor
import numpy as np
import soundfile as sf  # für das Laden des Signals
from scipy import signal
import sounddevice as sd


class ControlsGui(QWidget):
    def __init__(self, eqWindow: EqWindow.EqWindow, visualizer=None):
        super().__init__()
        self.visualizer = visualizer
        layoutV = QVBoxLayout(self)


        widget1 = QWidget()
        widget2 = QWidget()
        layout1 = QHBoxLayout(widget1)
        layout2 = QHBoxLayout(widget2)

        layoutV.addWidget(widget1)
        layoutV.addWidget(widget2)

        # widget1.setLayout(layout1)
        # widget2.setLayout(layout2)
        
        


        searchButton = QPushButton("Select Audio File", self)
        searchButton.clicked.connect(self.search_file)
        
        self.pause_play_button = QPushButton()
        self.pause_play_button.setIcon(
        self.pause_play_button.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )        
        self.pause_play_button.clicked.connect(self.play_pause_audio)
  

        positionSlider = QSlider(Qt.Orientation.Horizontal, self)
        positionSlider.sliderReleased.connect(lambda: AudioEngine.instance.play_audio(positionSlider.value() / 100.0))

        AudioEngine.instance.positionSlider = positionSlider

        layout1.addWidget(searchButton)
        layout1.addWidget(self.pause_play_button)
        layout1.addWidget(positionSlider)


        self.label = QLabel("No file selected")
        self.energy_label = QLabel("RMS Original: - | RMS Equalized: -")
        self.energy_label.setStyleSheet("color: #00e676; font-weight: bold;")
        
        self.recompute_button = QPushButton("Apply EQ & Recompute")
        self.recompute_button.clicked.connect(self.on_recompute_clicked)

        layout2.addWidget(self.label, 2)
        layout2.addWidget(self.energy_label, 3)
        layout2.addWidget(self.recompute_button, 1)

        # GUI timer to update progress slider and playback state safely in the GUI thread
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(100)  # every 100ms


    def on_recompute_clicked(self):
        # 1. Apply the current EQ curve to AudioEngine
        AudioEngine.instance.update_gains()
        # 2. Recompute the visualizer graphics
        if self.visualizer:
            self.visualizer.recompute_graphics()
        # 3. Update the energy label
        self.update_energy_status()


    def update_progress(self):
        engine = AudioEngine.instance
        if engine and engine.audio_loaded:
            if engine.playing:
                if engine.stream and not engine.stream.active:
                    engine.stop()
                    self.set_button(False)
                
                if hasattr(engine, 'positionSlider') and engine.positionSlider and not engine.positionSlider.isSliderDown():
                    total_frames = engine.ZxxL.shape[1]
                    if total_frames > 0:
                        val = min(100, int(engine.frame / total_frames * 100))
                        engine.positionSlider.blockSignals(True)
                        engine.positionSlider.setValue(val)
                        engine.positionSlider.blockSignals(False)


    def update_energy_status(self):
        status_str = AudioEngine.instance.get_energy_comparison()
        self.energy_label.setText(status_str)


    def set_button(self, paused: bool):
        self.pause_play_button.setIcon(
            self.pause_play_button.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause if paused else QStyle.StandardPixmap.SP_MediaPlay)
        )
        

    def play_pause_audio(self):
        if AudioEngine.instance.playing:
            self.set_button(False)
            AudioEngine.instance.stop()
        else:
            if AudioEngine.instance.audio_loaded:
                AudioEngine.instance.play_audio()
                self.set_button(True)



    def search_file(self):
        #open a file dialog to search for a file
        from PySide6.QtWidgets import QFileDialog
        file_dialog = QFileDialog(self)
        file_dialog.setDirectory(os.path.dirname(__file__) + "/..")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Audio Files (*.mp3 *.wav *.flac)")
        file_dialog.setViewMode(QFileDialog.ViewMode.List)
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            print(f"Selected file: {file_path}")
            # Signaldaten einlesen
            try:
                sig, sr = sf.read(file_path)
            except Exception as e:
                print(f"Fehler beim Lesen von {file_path}: {e}")
                return
            
            self.label.setText(os.path.basename(file_path))
            AudioEngine.instance.load_audio(sig, sr)
            AudioEngine.instance.frame = 0
            self.update_energy_status()
            if self.visualizer:
                self.visualizer.on_track_loaded()

