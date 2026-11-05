"""Тёмная тема в стиле макета Figma."""

MINT = "#00f0a8"
PINK = "#ff8fa6"
BLUE = "#4a9bff"
BG = "#0f1116"            # фон экранов — почти чёрный
SIDE = "#0a0c10"          # сайдбар — ещё темнее
CARD = "#1a1d24"          # карточка звука
CARD_HOVER = "#232833"
CARD_PLAY = "#123a2d"     # карточка во время воспроизведения
INPUT = "#15181e"
BORDER = "#1f7a5c"        # приглушённая мята для рамок
MUTED = "#8b93a1"         # вторичный текст

STYLE = f"""
* {{ font-family: "Inter", "Segoe UI", "Noto Sans", "DejaVu Sans", "Liberation Sans", sans-serif; font-size: 14px; color: #f4f4f4; }}
QMainWindow, QDialog, QStackedWidget {{ background: {BG}; }}
QWidget#page {{ background: {BG}; }}
QWidget#sidebar {{ background: {SIDE}; border-right: 1px solid {BORDER}; }}
QLabel#total {{ border: 1px solid {BORDER}; border-radius: 14px; padding: 6px 8px; background: {SIDE}; font-size: 13px; }}
QLabel {{ background: transparent; }}

QPushButton {{ border: none; border-radius: 5px; padding: 7px 14px; color: #ffffff; background: #24272f; }}
QPushButton:hover {{ background: #2f3540; }}
QPushButton#green {{ background: {MINT}; color: #06241a; font-weight: 600; }}
QPushButton#green:hover {{ background: #4dffc6; }}
QPushButton#red {{ background: {PINK}; color: #3a0a15; font-weight: 600; }}
QPushButton#red:hover {{ background: #ffa9bb; }}
QPushButton#blue {{ background: {BLUE}; color: #ffffff; font-weight: 600; }}
QPushButton#blue:hover {{ background: #70b0ff; }}
QPushButton#gear {{ background: {MINT}; color: #06241a; font-size: 20px; padding: 2px 8px; }}
QPushButton#mini {{ background: #ff2d2d; padding: 0; min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px; font-size: 9px; border-radius: 2px; }}
QPushButton#loop {{ background: #24272f; border: 1px solid #2f3540; border-radius: 5px; padding: 0; color: {MUTED}; font-size: 15px; }}
QPushButton#loop:hover {{ background: #2f3540; color: #ffffff; }}
QPushButton#loop:checked {{ background: {MINT}; border: 1px solid {MINT}; color: #06241a; font-weight: 700; }}

QLineEdit, QComboBox {{ background: {INPUT}; border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 10px; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {MINT}; }}
QLineEdit#search {{ border: none; background: {INPUT}; }}
QPushButton#category {{ background: {MINT}; color: #06241a; font-weight: 600; border-radius: 4px; padding: 7px 14px; }}
QPushButton#category:hover {{ background: #4dffc6; }}
QListWidget {{ background: {INPUT}; border: 1px solid {BORDER}; border-radius: 6px; padding: 4px; }}
QListWidget::item {{ padding: 8px; }}
QListWidget::item:selected {{ background: {BORDER}; color: #ffffff; }}
QComboBox QAbstractItemView {{ background: {INPUT}; selection-background-color: {BORDER}; }}
QLineEdit#hotkeyEdit {{ font-size: 18px; font-weight: 600; }}

QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; }}
QFrame#card:hover {{ background: {CARD_HOVER}; }}
QFrame#card[playing="true"] {{ border: 2px solid {MINT}; background: {CARD_PLAY}; }}
QFrame#card[empty="true"] {{ background: {INPUT}; border: 1px solid #1a4a3a; }}
QFrame#card[empty="true"]:hover {{ background: #1b2028; }}
QFrame#card QLabel {{ background: transparent; font-size: 17px; }}
QFrame#card QLabel#cardIcon {{ background: #d9d9d9; color: #1b1e24; border-radius: 19px; font-size: 18px; }}
QFrame#card QLabel#badge {{ background: #e9e9e9; color: #262a31; border-radius: 3px; padding: 0 8px; font-size: 14px; }}
QFrame#card QLabel#cardName {{ font-size: 14px; }}
QFrame#card QLabel#cardTime {{ font-size: 10px; color: {MUTED}; }}
QFrame#card QLabel#cardVol {{ font-size: 12px; color: {MUTED}; }}

QSlider#seek::groove:horizontal {{ height: 4px; background: #2a2f38; border-radius: 2px; }}
QSlider#seek::sub-page:horizontal {{ background: {MINT}; border-radius: 2px; }}
QSlider#seek::add-page:horizontal {{ background: #2a2f38; border-radius: 2px; }}
QSlider#seek::handle:horizontal {{ background: #ffffff; width: 10px; margin: -4px 0; border-radius: 5px; }}
QSlider#volume::groove:horizontal {{ height: 3px; background: #2a2f38; border-radius: 2px; }}
QSlider#volume::sub-page:horizontal {{ background: #7f8a99; border-radius: 2px; }}
QSlider#volume::add-page:horizontal {{ background: #2a2f38; border-radius: 2px; }}
QSlider#volume::handle:horizontal {{ background: #c9d1dc; width: 9px; margin: -3px 0; border-radius: 5px; }}
QSlider#master::groove:horizontal {{ height: 5px; background: #2a2f38; border-radius: 3px; }}
QSlider#master::sub-page:horizontal {{ background: {MINT}; border-radius: 3px; }}
QSlider#master::add-page:horizontal {{ background: #2a2f38; border-radius: 3px; }}
QSlider#master::handle:horizontal {{ background: #ffffff; width: 12px; margin: -4px 0; border-radius: 6px; }}
QLabel#masterLabel {{ color: {MUTED}; font-size: 12px; }}
QLabel#masterValue {{ color: {MUTED}; font-size: 12px; }}

QFrame#nowPanel {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 6px; }}
QFrame#nowRow {{ background: {MINT}; border-radius: 2px; }}
QFrame#nowRow QLabel {{ color: #06241a; font-size: 17px; }}
QFrame#dropZone {{ background: {INPUT}; border: 1px solid {BORDER}; border-radius: 8px; }}
QFrame#group {{ background: {INPUT}; border: 1px solid {BORDER}; border-radius: 6px; }}
QFrame#group QLabel, QFrame#group QCheckBox {{ background: transparent; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #2a2f38; border-radius: 5px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: #3a414d; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QSlider::groove:horizontal {{ height: 6px; background: #2a2f38; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: #ffffff; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 14px; margin: -5px 0; border-radius: 7px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid #aaa; border-radius: 2px; background: #ffffff; }}
QCheckBox::indicator:checked {{ background: {MINT}; border: 1px solid {MINT}; }}
QMenu {{ background: {INPUT}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; }}
QMenu::item:selected {{ background: {BORDER}; }}
QStatusBar {{ background: {SIDE}; }}
QStatusBar QLabel {{ color: {PINK}; }}
QToolTip {{ background: {INPUT}; color: white; border: 1px solid {BORDER}; }}
"""
