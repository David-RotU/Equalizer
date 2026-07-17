from gui.ControlPoint import ControlPoint
from PySide6.QtCore import QPointF, QSize, Qt, QLineF
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor
import numpy as np


class EqWindow(QWidget):

    points = [
		    QPointF(.3, .5),
		    QPointF(.3, .2)
    ]

    selected = -1
    dragging = False
    radius = 6


    def __init__(self):
        super().__init__()
        self.freqs = np.zeros(5)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.sliders = []


        
    def update_frequencies(self, frequencies):
        self.freqs = frequencies
        self.update()


    def lerp(self, color1: QColor, color2: QColor, t: float) -> QColor:
        r = int(color1.red() + (color2.red() - color1.red()) * t)
        g = int(color1.green() + (color2.green() - color1.green()) * t)
        b = int(color1.blue() + (color2.blue() - color1.blue()) * t)
        return QColor(r, g, b)
    

    def paintEvent(self, event):
        with QPainter(self) as painter:
            painter.fillRect(self.rect(), QColor(40, 40, 40))

            # paint Frequencies
            for i in range(len(self.freqs)):
                value = abs(self.freqs[i]) / 256
                x = (i + 0.5) / len(self.freqs)
                y = 1 - np.clip(value, 0, 1)
                color = self.lerp(QColor(100, 255, 100), QColor(255, 100, 100), np.clip(value, 0, 1))
                painter.setPen(QPen(color, 2))
                painter.drawLine(
                    self.toScreenPos(QPointF(x, 1)),
                    self.toScreenPos(QPointF(x, y))
                )


            # Polynomobjekt


            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            #Borders
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            left = int(self.width() * 0.05)
            top = int(self.height() * 0.05)
            painter.drawRect(self.rect().adjusted(left, top, -left, -top))

         
            



            # Draw points
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)


            # Kontrollpunkt
            for i, p in enumerate(self.points):
                point_pos = self.toScreenPos(p)

                painter.setBrush(Qt.GlobalColor.white if i != self.selected else Qt.GlobalColor.red)
                painter.drawEllipse(point_pos, 6, 6)

            #Linie
            if len(self.points) == 0:
                return

            painter.setPen(QPen(QColor(100,100,200), 2))

            if self.points[0].x() >0:
                painter.drawLine(QLineF(self.toScreenPos(QPointF(0, self.points[0].y())), self.toScreenPos(self.points[0])))

            if self.points[-1].x() <1:
                painter.drawLine(QLineF(self.toScreenPos(QPointF(1, self.points[-1].y())), self.toScreenPos(self.points[-1])))

            for i in range(len(self.points)-1):
                painter.drawLine(QLineF(self.toScreenPos(self.points[i]), self.toScreenPos(self.points[i+1])))


    def interpolate(self, f: float) -> float:
        from audio.eq_curve import EqCurve
        pts = [(p.x(), p.y()) for p in self.points]
        curve = EqCurve(pts)
        return curve.interpolate(f) 

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.selected = -1

        for i, point in enumerate(self.points):
            if QLineF(event.position(), self.toScreenPos(point)).length() <= self.radius + 2:
                self.selected = i
                self.dragging = True
                break

        self.update()
    

    def mouseDoubleClickEvent(self, event):
        newPoint = self.screenPosToModel(event.position())

        self.points.append(newPoint)
        self.points.sort(key=lambda p: p.x())
        self.selected = self.points.index(newPoint)
        self.update()
        self.update_sliders()
        

    def mouseMoveEvent(self, event):
        if self.dragging and self.selected >= 0:
            self.points[self.selected] = self.screenPosToModel(event.position())
            dragged_point = self.points[self.selected]
            self.points.sort(key=lambda p: p.x())
            self.selected = self.points.index(dragged_point)

            self.update()
            self.update_sliders()
    
    
    def toScreenPos(self, pos: QPointF) -> QPointF:
        borderL = self.width() * 0.05
        borderR = self.width() * 0.95
        borderU = self.height() * 0.05
        borderD = self.height() * 0.95

        return QPointF(pos.x() * (borderR-borderL) + borderL, pos.y() * (borderD-borderU) + borderU)


    def screenPosToModel(self, pos: QPointF) -> QPointF:
        borderL = self.width() * 0.05
        borderR = self.width() * 0.95
        borderU = self.height() * 0.05
        borderD = self.height() * 0.95

        return QPointF(np.clip((pos.x()-borderL) / (borderR-borderL), 0, 1), np.clip((pos.y() -borderU) / (borderD-borderU), 0, 1))


    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.update_sliders()



    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete and self.selected >= 0:
            self.points.pop(self.selected)
            self.selected = -1
            self.update()
            self.update_sliders()
            
    def set_gain(self, index, value):
        # Map index 0..4 to x positions 0.1, 0.3, 0.5, 0.7, 0.9
        x_target = 0.1 + index * 0.2
        # Find if a point is close to x_target
        threshold = 0.08
        found = False
        for p in self.points:
            if abs(p.x() - x_target) < threshold:
                p.setY(1.0 - value)
                found = True
                break
        if not found:
            self.points.append(QPointF(x_target, 1.0 - value))
            self.points.sort(key=lambda p: p.x())
            
        self.update()
        pass

    def update_sliders(self):
        if not hasattr(self, 'sliders') or not self.sliders:
            return
        for i, slider in enumerate(self.sliders):
            x_target = 0.1 + i * 0.2
            threshold = 0.1
            closest_point = None
            min_dist = float('inf')
            for p in self.points:
                dist = abs(p.x() - x_target)
                if dist < threshold and dist < min_dist:
                    min_dist = dist
                    closest_point = p
            if closest_point is not None:
                slider.blockSignals(True)
                slider.setValue(int((1.0 - closest_point.y()) * 100))
                slider.blockSignals(False)



# #main test
# app = QApplication(sys.argv)

# window = EqWindow()
# window.show()

# app.exec()