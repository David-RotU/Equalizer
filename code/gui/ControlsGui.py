import os
from signal import signal
import sys

import gui.EqWindow
from AudioEngine import AudioEngine
from gui.ControlPoint import ControlPoint
from PySide6.QtCore import QPointF, QSize, Qt, QLineF
from PySide6.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QMainWindow, QPushButton, QSlider, QStyle, QWidget
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPen, QColor
import numpy as np
import soundfile as sf  # für das Laden des Signals
from scipy import signal
import sounddevice as sd


class ControlsGui(QWidget):
    def __init__(self, eqWindow: EqWindow.EqWindow):
        super().__init__()
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
        
        pause_play_button = QPushButton()
        pause_play_button.setIcon(
        pause_play_button.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )        
        pause_play_button.clicked.connect(self.play_pause_audio)
  

        positionSlider = QSlider(Qt.Orientation.Horizontal, self)
        positionSlider.sliderReleased.connect(lambda: AudioEngine.instance.play_audio(positionSlider.value() / 100.0))

        AudioEngine.instance.positionSlider = positionSlider

        layout1.addWidget(searchButton)
        layout1.addWidget(pause_play_button)
        layout1.addWidget(positionSlider)


        self.label = QLabel()
        self.verify_energy_button = QPushButton("Verify Energy")
        self.verify_energy_button.pressed.connect(self.verify_energy)
        # self.label.setText("")

        layout2.addWidget(self.label)
        layout2.addWidget(self.verify_energy_button)


    def verify_energy(self):
        AudioEngine.instance.compare_energy()


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
                print(f"Fehler beim Lesen von {filename}: {e}")
                return
            
            self.label.setText(os.path.basename(file_path))
            AudioEngine.instance.load_audio(sig, sr)
            AudioEngine.instance.frame = 0

