import pyqtgraph as pg
import numpy as np


class PlotMultiCurveItem(pg.QtGui.QGraphicsPathItem):
    def __init__(self, x, y, c='w'):
        """
        An alternative to pyqtgraph.PlotCurveItem, offers better performance when plotting multiple curves. x and y must be same shape (n_curves, n_samples_per_curve)

        :param x: x coords, numpy.ndarray with shape (n_curves, n_samples_per_curve)
        :param y: y coords, numpy.ndarray with shape (n_curves, n_samples_per_curve)
        :param c: colors, see pyqtgraph.mkPen
        """
        connect = np.ones(y.shape, dtype=bool)
        connect[:, -1] = False
        self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect.flatten())
        super().__init__(self.path)
        self.setPen(pg.mkPen(c))

    def boudingRect(self):
        return self.path.boundingRect()
