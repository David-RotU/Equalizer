import sys
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from AudioEngine import AudioEngine
from gui.PlayheadOverlay import PlayheadOverlay

class DbTrackWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create matplotlib Figure and Canvas
        self.figure = Figure(facecolor='#282828')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Style variables
        self.dark_bg = '#1e1e1e'
        self.text_color = '#e0e0e0'
        self.grid_color = '#444444'
        
        # Setup subplot
        self.ax = self.figure.add_subplot(1, 1, 1, facecolor=self.dark_bg)
        self.ax.set_title("Track Loudness Profile (dB over Time)", color=self.text_color, fontsize=10, pad=5)
        self.ax.set_ylabel("Level (dB)", color=self.text_color, fontsize=8)
        self.ax.set_xlabel("Time (seconds)", color=self.text_color, fontsize=8)
        
        # Adjust margins
        self.figure.subplots_adjust(top=0.88, bottom=0.20, left=0.10, right=0.95)
        
        # Grid and spines
        self.ax.grid(True, which='both', color=self.grid_color, linestyle=':', alpha=0.4)
        self.ax.tick_params(colors=self.text_color, labelsize=8)
        for spine in ['top', 'right']:
            self.ax.spines[spine].set_visible(False)
        self.ax.spines['left'].set_color(self.grid_color)
        self.ax.spines['bottom'].set_color(self.grid_color)
        
        # Initial bounds
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(-80, 5)
        
        # Plot lines placeholder
        self.time_axis = np.linspace(0, 10, 1000)
        self.line_orig, = self.ax.plot(self.time_axis, np.ones(1000) * -80, color='#7c4dff', alpha=0.6, linewidth=1.5, label='Original')
        self.line_recon, = self.ax.plot(self.time_axis, np.ones(1000) * -80, color='#00e676', alpha=0.8, linewidth=1.5, label='Equalized')
        
        # Setup playhead overlay via Qt
        self.overlay = PlayheadOverlay(self.canvas, self.get_overlay_lines)
        
        # Legend with dark theme styling
        self.legend = self.ax.legend(loc='lower left', fontsize=8, framealpha=0.2, facecolor='#282828', edgecolor=self.grid_color)
        for text in self.legend.get_texts():
            text.set_color(self.text_color)
            
    def on_track_loaded(self):
        engine = AudioEngine.instance
        if not engine or not engine.audio_loaded:
            return
            
        total_duration = len(engine.sig) / engine.sample_rate
        self.time_axis = np.linspace(0, total_duration, 1000)
        
        # Set x limits to match duration
        self.ax.set_xlim(0, total_duration)
        
        # Update lines with real loaded envelope data
        if engine.db_envelope_orig is not None:
            self.line_orig.set_xdata(self.time_axis)
            self.line_orig.set_ydata(engine.db_envelope_orig)
            
        self.recompute_graphics()
        
    def recompute_graphics(self):
        engine = AudioEngine.instance
        if not engine or not engine.audio_loaded:
            return
            
        if engine.db_envelope_recon is not None:
            self.line_recon.set_xdata(self.time_axis)
            self.line_recon.set_ydata(engine.db_envelope_recon)
            
        self.canvas.draw()
        self.overlay.update()
        
    def update_playhead(self):
        engine = AudioEngine.instance
        if not engine or not engine.audio_loaded or self.time_axis is None:
            return
            
        self.overlay.update()

    def get_overlay_lines(self):
        engine = AudioEngine.instance
        if not engine or not engine.audio_loaded or self.time_axis is None:
            return []
            
        if hasattr(engine, 'positionSlider') and engine.positionSlider:
            ratio = engine.positionSlider.value() / 100.0
        else:
            ratio = engine.frame / max(1, engine.ZxxL.shape[1])
            
        dpr = float(self.canvas.devicePixelRatio())
        canvas_height = self.canvas.height()
        
        ax = self.ax
        bbox = ax.get_window_extent()
        x0 = bbox.x0 / dpr
        x1 = bbox.x1 / dpr
        y0 = bbox.y0 / dpr
        y1 = bbox.y1 / dpr
        
        x = x0 + ratio * (x1 - x0)
        y_top = canvas_height - y1
        y_bottom = canvas_height - y0
        
        return [(x, y_top, y_bottom)]
