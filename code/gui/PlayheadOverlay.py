from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPainter, QPen, QColor

class PlayheadOverlay(QWidget):
    def __init__(self, parent_canvas, get_lines_callback):
        super().__init__(parent_canvas)
        # Configure transparency and mouse interaction
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self.get_lines_callback = get_lines_callback
        
        # Install event filter to track canvas size changes
        parent_canvas.installEventFilter(self)
        self.setGeometry(0, 0, parent_canvas.width(), parent_canvas.height())
        
    def eventFilter(self, watched, event):
        if watched == self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(0, 0, watched.width(), watched.height())
        return super().eventFilter(watched, event)
        
    def paintEvent(self, event):
        lines = self.get_lines_callback()
        if not lines:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor('#ff5252'), 1.5)
        painter.setPen(pen)
        
        for x, y0, y1 in lines:
            painter.drawLine(int(x), int(y0), int(x), int(y1))
