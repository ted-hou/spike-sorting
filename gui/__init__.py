# noinspection PyPep8Naming
from PyQt6.QtGui import QColor

_default_colors = ('red', 'green', 'darkblue', 'skyblue', 'magenta', 'gold', 'black')


def default_color(i: int):
    i = i % len(_default_colors)
    return QColor(_default_colors[i])


def getColor(index: int = 0, count: int = 1):
    return QColor.fromHslF(index / count, 0.5, 0.5, 1.0)