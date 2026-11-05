"""Приведение клавиш из Qt и pynput к единому виду ('q', '1', 'f5', 'space').

Русская раскладка переводится в латиницу по положению клавиши,
поэтому горячая клавиша Q работает и при включённой русской раскладке.
"""
from PyQt6.QtCore import Qt

_RU = dict(zip("йцукенгшщзхъфывапролджэячсмитьбю",
               "qwertyuiop[]asdfghjkl;'zxcvbnm,."))

_IGNORED_QT = {k.value for k in (
    Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
    Qt.Key.Key_AltGr, Qt.Key.Key_CapsLock, Qt.Key.Key_NumLock,
    Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab, Qt.Key.Key_Backtab,
    Qt.Key.Key_unknown)}

_IGNORED_PYNPUT = ("shift", "ctrl", "alt", "cmd", "caps", "num", "enter", "tab")


def _fix(name: str) -> str:
    name = name.lower()
    return _RU.get(name, name)


def from_qt_event(event) -> str:
    """Клавиша из QKeyEvent. Пустая строка, если это не горячая клавиша."""
    if event.key() in _IGNORED_QT:
        return ""
    mods = event.modifiers()
    if mods & (Qt.KeyboardModifier.ControlModifier
               | Qt.KeyboardModifier.AltModifier
               | Qt.KeyboardModifier.MetaModifier):
        return ""
    from PyQt6.QtGui import QKeySequence
    name = QKeySequence(event.key()).toString() or event.text()
    return _fix(name) if name else ""


def from_pynput(key) -> str:
    """Приводит клавишу pynput к единому виду ('q', '1', 'f5', 'space')."""
    char = getattr(key, "char", None)
    if char and char.isprintable():
        return _fix(char)
    name = getattr(key, "name", None)
    if name and not name.startswith(_IGNORED_PYNPUT):
        return name.lower()
    return ""


def pretty(key: str) -> str:
    """Как показывать клавишу на карточке."""
    if not key:
        return ""
    return key.upper() if len(key) == 1 else key.capitalize()
