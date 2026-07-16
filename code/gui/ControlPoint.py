from dataclasses import dataclass
from PySide6.QtCore import QPointF

@dataclass
class ControlPoint:
	position: QPointF
	handle_in: QPointF
	handle_out: QPointF

