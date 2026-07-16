import sys
from . import EqWindow
from gui.ControlsGui import ControlsGui
from PySide6.QtCore import QSize, Qt
from AudioEngine import AudioEngine
from PySide6.QtWidgets import QApplication, QMainWindow, QMenuBar, QPushButton, QSlider, QVBoxLayout, QHBoxLayout, QWidget
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Equalizer")
        central_widget = QWidget()
        eq_Widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        eq_layout = QHBoxLayout(eq_Widget)

        eq_window = EqWindow.EqWindow()
        AudioEngine.instance = AudioEngine(eq_window) 

        eq_layout.addWidget(eq_window, 1)
        for i in range(5):
            slider = QSlider(Qt.Orientation.Vertical)
            eq_layout.addWidget(slider, 0)
            slider.sliderMoved.connect(lambda value, index=i: eq_window.set_gain(index, value / 100.0))

        layout.addWidget(ControlsGui(eq_window), 0)
        layout.addWidget(eq_Widget, 1)

        central_widget.setLayout(layout)
        eq_Widget.setLayout(eq_layout)

def main():
    app = QApplication([])
    #app.setStyle("Fusion")
    window = MainWindow()
    window.showMaximized()

    app.exec()
    app.quit()


