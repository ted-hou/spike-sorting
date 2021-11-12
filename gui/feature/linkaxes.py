from pyqtgraph import ViewBox
import weakref
import pyqtgraph as pg


# noinspection PyPep8Naming
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
            getattr(oldSrcView,
                    oldSignal).disconnect()  # This diconnect everything, might conflict with native functionality

    # Connect new
    if srcAxis == ViewBox.XAxis:
        signal = 'sigXRangeChanged'
    else:
        signal = 'sigYRangeChanged'

    getattr(srcView, signal).connect(tgtView.axisLinkSlot[tgtAxis])
    tgtView.axisLinkSrc[tgtAxis] = (weakref.ref(srcView), srcAxis)

    if reciprocal:
        linkAxes(tgtView, srcView, tgtAxis, srcAxis, reciprocal=False)


# noinspection PyPep8Naming
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
