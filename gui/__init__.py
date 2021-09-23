from PyQt5.QtGui import QColor

_default_colors = ('red', 'green', 'darkblue', 'skyblue', 'magenta', 'gold', 'black')


def default_color(i: int):
    i = i % len(_default_colors)
    return QColor(_default_colors[i])
