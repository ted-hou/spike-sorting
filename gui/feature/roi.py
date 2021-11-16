import numpy as np
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainterPath, QPainter
import pyqtgraph as pg
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent
from pyqtgraph.graphicsItems.ROI import ROI, Handle, Point
from matplotlib import path

# noinspection PyPep8Naming
class PolygonROI(ROI):
    """
    Right click to add a point.
    Ctrl+Right click to remove last point.
    """
    _scene: pg.GraphicsScene = None
    _menuEnabled = True
    _completed = False

    def __init__(self, positions, scene: pg.GraphicsScene, **args):
        super(PolygonROI, self).__init__([0, 0], [1, 1], movable=False, removable=False, **args)
        for p in positions:
            self.addFreeHandle(p)
        self.setZValue(1000)
        self._scene = scene
        self._menuEnabled = True
        self._completed = False

    def paint(self, p, *args):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(self.currentPen)
        for i in range(len(self.handles)):
            h1 = self.handles[i]['item'].pos()
            h2 = self.handles[i - 1]['item'].pos()
            p.drawLine(h1, h2)

    def boundingRect(self):
        r = QRectF()
        for h in self.handles:
            r |= self.mapFromItem(h['item'],
                                  h['item'].boundingRect()).boundingRect()  ## |= gives the union of the two QRectFs
        return r

    def shape(self):
        p = QPainterPath()
        p.moveTo(self.handles[0]['item'].pos())
        for i in range(len(self.handles)):
            p.lineTo(self.handles[i]['item'].pos())
        return p

    def stateCopy(self):
        sc = {}
        sc['pos'] = Point(self.state['pos'])
        sc['size'] = Point(self.state['size'])
        sc['angle'] = self.state['angle']
        return sc

    def addOrRemovePoint(self, ev: MouseClickEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()
            pos = self.getViewBox().mapSceneToView(ev.scenePos())
            self.addFreeHandle(pos)
        elif ev.button() == Qt.MouseButton.RightButton and len(self.handles) > 1:
            print(len(self.handles), '\n', *self.handles)
            ev.accept()
            self.removeHandle(self.handles[-1]['item'])
            self.moveLastPoint(ev.scenePos())

    def moveLastPoint(self, pos: QPointF):
        self.movePoint(self.handles[-1]['item'], pos, coords='scene')

    def startDrawing(self):
        """Start listening to sigMouseMoved and sigMouseClicked events."""
        self._completed = False
        self._scene.sigMouseMoved.connect(self.moveLastPoint)
        self._scene.sigMouseClicked.connect(self.addOrRemovePoint)
        self._menuEnabled = self.getViewBox().menuEnabled()
        self.getViewBox().setMenuEnabled(False)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def completeDrawing(self):
        """Call to finish drawing the polygon."""
        self.removeHandle(self.handles[-1]['item'])
        self._scene.sigMouseMoved.disconnect(self.moveLastPoint)
        self._scene.sigMouseClicked.disconnect(self.addOrRemovePoint)
        self.getViewBox().setMenuEnabled(self._menuEnabled)
        self.unsetCursor()
        self._completed = True

    @property
    def completed(self) -> bool:
        return self._completed

    def contains_points(self, points: np.ndarray) -> np.ndarray:
        p = path.Path([(hInfo['pos'].x(), hInfo['pos'].y()) for hInfo in self.handles])
        return p.contains_points(points)

