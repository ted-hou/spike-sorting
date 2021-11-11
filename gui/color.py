from __future__ import annotations
import typing
from PyQt6.QtGui import QColor

_default_colors = ('red', 'green', 'darkblue', 'skyblue', 'magenta', 'gold', 'black')


def default_color(i: int):
    i = i % len(_default_colors)
    return QColor(_default_colors[i])


# noinspection PyPep8Naming
class ColorRange:
    _color: QColor
    _hRange: typing.Sequence[float]
    _sRange: typing.Sequence[float]
    _lRange: typing.Sequence[float]

    @property
    def color(self):
        return self._color

    @property
    def hRange(self):
        return self._hRange

    @property
    def sRange(self):
        return self._sRange

    @property
    def lRange(self):
        return self._lRange

    @property
    def width(self) -> float:
        """Value between 0.0 and 1.0, indicating the range of colors contained. width = hueRange * 0.9 + saturationRange * 0.09 + lightnessRange * 0.01"""
        return (self.hRange[1] - self.hRange[0]) * 0.9 + (self.sRange[1] - self.sRange[0]) * 0.09 + self.lRange[1] - self.lRange[0] * 0.01

    def __init__(self, hRange=(0.0, 1.0), sRange=(.75, 0.25), lRange=(0.5, 0.25)):
        self._hRange = hRange
        self._sRange = sRange
        self._lRange = lRange
        self._color = QColor.fromHslF(self._hRange[0], self._sRange[0], self._lRange[0])

    def split(self, count: int, method: str = None) -> list[ColorRange]:
        if count <= 1:
            return [ColorRange(self._hRange, self._sRange, self._lRange)]

        if method is None:
            if self._hRange[1] - self._hRange[0] > 1 / 8:
                method = 'hue'
            elif self._sRange[1] - self._lRange[0] > 1 / 8:
                method = 'saturation'
            else:
                method = 'lightness'

        ranges = []
        for i in range(count):
            if method in ('hue', 'h'):
                hRange = (self._lerp(self._hRange, i / count), self._lerp(self._hRange, (i + 1) / count))
                ranges.append(ColorRange(hRange, self._sRange, self._lRange))
            elif method in ('saturation', 's', 'sat'):
                sRange = (self._lerp(self._sRange, i / count), self._lerp(self._sRange, (i + 1) / count))
                ranges.append(ColorRange(self._hRange, sRange, self._lRange))
            elif method in ('lightness', 'l', 'light', 'li'):
                lRange = (self._lerp(self._lRange, i / count), self._lerp(self._lRange, (i + 1) / count))
                ranges.append(ColorRange(self._hRange, self._sRange, lRange))
        return ranges

    @staticmethod
    def _lerp(r: typing.Sequence[float], t: float):
        return (r[1] - r[0]) * t + r[0]

    @staticmethod
    def black():
        return ColorRange(hRange=(0.0, 0.0), sRange=(0.0, 0.0), lRange=(0.0, 0.0))
