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

        self.setWindowTitle("Equalizer Dashboard")
        self.setMinimumSize(QSize(1100, 650))
        
        # Apply visual styles to PySide6 components
        self.setStyleSheet("""
            QMainWindow {
                background-color: #282828;
            }
            QWidget {
                background-color: #282828;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #383838;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #00e676;
            }
            QPushButton:pressed {
                background-color: #242424;
            }
            QSlider::groove:vertical {
                background: #1e1e1e;
                width: 6px;
                border-radius: 3px;
            }
            QSlider::handle:vertical {
                background: #00e676;
                border: 1px solid #1e1e1e;
                height: 16px;
                width: 16px;
                margin: 0 -5px;
                border-radius: 8px;
            }
            QSlider::handle:vertical:hover {
                background: #00ff87;
            }
            QSlider::groove:horizontal {
                background: #1e1e1e;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #7c4dff;
                border: 1px solid #1e1e1e;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #b388ff;
            }
            QLabel {
                font-size: 12px;
                font-weight: 500;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        eq_Widget = QWidget()
        eq_layout = QHBoxLayout(eq_Widget)
        eq_layout.setContentsMargins(10, 10, 10, 10)

        eq_window = EqWindow.EqWindow()
        AudioEngine.instance = AudioEngine(eq_window) 

        eq_layout.addWidget(eq_window, 1)
        for i in range(5):
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(0, 100)
            slider.setValue(50)
            eq_layout.addWidget(slider, 0)
            slider.sliderMoved.connect(lambda value, index=i: eq_window.set_gain(index, value / 100.0))
            eq_window.sliders.append(slider)

        eq_window.update_sliders()

        # Instantiate VisualizerWidget early to pass callback
        from gui.VisualizerWidget import VisualizerWidget
        self.visualizer = VisualizerWidget()

        # Arrange EQ window and Visualizer side-by-side
        main_content_widget = QWidget()
        main_content_layout = QHBoxLayout(main_content_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(15)
        
        main_content_layout.addWidget(eq_Widget, 4)
        main_content_layout.addWidget(self.visualizer, 5)

        layout.addWidget(ControlsGui(eq_window, self.visualizer), 0)
        layout.addWidget(main_content_widget, 1)

        central_widget.setLayout(layout)
        eq_Widget.setLayout(eq_layout)

def main():
    app = QApplication([])
    window = MainWindow()
    window.showMaximized()

    app.exec()
    app.quit()


