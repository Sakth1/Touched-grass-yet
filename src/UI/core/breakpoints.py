from enum import Enum, auto


class WindowWidthClass(Enum):
    COMPACT = auto()
    MEDIUM = auto()
    EXPANDED = auto()


COMPACT_MAX = 599
MEDIUM_MAX = 899


def classify_width(width: float) -> WindowWidthClass:
    if width < 600:
        return WindowWidthClass.COMPACT
    elif width < 900:
        return WindowWidthClass.MEDIUM
    return WindowWidthClass.EXPANDED


def sidebar_collapsed(width_class: WindowWidthClass) -> bool:
    return width_class != WindowWidthClass.EXPANDED


def context_collapsed(width_class: WindowWidthClass) -> bool:
    return width_class not in (WindowWidthClass.EXPANDED, WindowWidthClass.MEDIUM)





