import numpy as np
from PyQt5.QtWidgets import QGraphicsPathItem
import pyqtgraph as pg
from pyqtgraph import ViewBox
import weakref

class MultiCurvePlotItem(QGraphicsPathItem):
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


def linkAxes(srcView: ViewBox, tgtView: ViewBox, srcAxis: int, tgtAxis: int, reciprocal=True):
    if not hasattr(tgtView, 'axisLinkSlot'):
        tgtView.axisLinkSlot = [None, None]
    if not hasattr(tgtView, 'axisLinkSrc'):
        tgtView.axisLinkSrc = [None, None]

    tgtView.axisLinkSlot[tgtAxis] = lambda _, value: _updateAxisFromLinkedView(srcView, tgtView, tgtAxis, value)

    # Disconnect old
    if tgtView.axisLinkSrc[tgtAxis] is not None:
        (oldSrcView, oldSrcAxis) = tgtView.axisLinkSrc[tgtAxis]
        oldSrcView = oldSrcView()
        if oldSrcView is not None:
            oldSignal = 'sigXRangeChanged' if oldSrcAxis == ViewBox.XAxis else 'sigYRangeChanged'
            getattr(oldSrcView, oldSignal).disconnect() # This diconnect everything, might conflict with native functionality

    # Connect new
    if srcAxis == ViewBox.XAxis:
        signal = 'sigXRangeChanged'
    else:
        signal = 'sigYRangeChanged'

    getattr(srcView, signal).connect(tgtView.axisLinkSlot[tgtAxis])
    tgtView.axisLinkSrc[tgtAxis] = (weakref.ref(srcView), srcAxis)

    if reciprocal:
        linkAxes(tgtView, srcView, tgtAxis, srcAxis, reciprocal=False)

def _updateAxisFromLinkedView(src: ViewBox, tgt: ViewBox, axis: int, value: tuple):
    if tgt.linksBlocked:
        return

    src.blockLink(True)
    try:
        if axis == pg.ViewBox.XAxis:
            tgt.setRange(xRange=value, padding=0, update=True)
        elif axis == pg.ViewBox.YAxis:
            tgt.setRange(yRange=value, padding=0, update=True)
    finally:
        src.blockLink(False)