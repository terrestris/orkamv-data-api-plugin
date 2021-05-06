from qgis.gui import QgsMapTool, QgsMapToolEmitPoint, QgsRubberBand, QgisInterface, QgsMapCanvas
from qgis.core import QgsWkbTypes, QgsPointXY, QgsRectangle
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from typing import Tuple, Optional


class DrawExtent(QgsMapToolEmitPoint):
    selection_done = pyqtSignal()

    def __init__(self, iface: QgisInterface):
        self.canvas: QgsMapCanvas = iface.mapCanvas()
        super().__init__(self.canvas)
        self.iface = iface
        self.canvas.setMapTool(self)

        self.startPoint: Optional[QgsPointXY] = None
        self.endPoint: Optional[QgsPointXY] = None
        self.isEmittingPoint = False

        self.rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rb.setColor(QColor(60, 151, 255, 255))
        self.reset()

    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rb.reset(True)

    def canvasPressEvent(self, e):
        if not e.button() == Qt.LeftButton:
            return
        self.startPoint = self.toMapCoordinates(e.pos())
        self.isEmittingPoint = True

    def canvasReleaseEvent(self, e):
        self.isEmittingPoint = False
        if not e.button() == Qt.LeftButton:
            return None
        if self.rb.numberOfVertices() > 3:
            self.isEmittingPoint = False
            self.selection_done.emit()
        else:
            self.reset()

    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return
        self.endPoint = self.toMapCoordinates(e.pos())
        self.show_rect(self.startPoint, self.endPoint)

    def show_rect(self, start_point: QgsPointXY, end_point: QgsPointXY):
        self.rb.reset(QgsWkbTypes.PolygonGeometry)  # true, it's a polygon
        if start_point.x() == end_point.x() or start_point.y() == end_point.y():
            return

        point1 = QgsPointXY(start_point.x(), start_point.y())
        point2 = QgsPointXY(start_point.x(), end_point.y())
        point3 = QgsPointXY(end_point.x(), end_point.y())
        point4 = QgsPointXY(end_point.x(), start_point.y())

        self.rb.addPoint(point1, False)
        self.rb.addPoint(point2, False)
        self.rb.addPoint(point3, False)
        self.rb.addPoint(point4, True)  # true to update canvas
        self.rb.show()

    def deactivate(self):
        self.rb.reset(True)
        QgsMapTool.deactivate(self)

    def get_bbox(self) -> Optional[QgsRectangle]:
        if self.startPoint is None or self.endPoint is None:
            return None

        return QgsRectangle(self.startPoint, self.endPoint)
