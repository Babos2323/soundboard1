"""MainWindow (View + Controller): два экрана по макету Figma — главный и «Библиотека».

На главном экране карточка звука содержит встроенные регуляторы:
перемотку (полоса прогресса), зацикливание и громкость конкретного звука.
Список карточек прокручивается колесом мыши, а сетка всегда продолжается вниз,
поэтому прокрутка работает и при небольшом количестве звуков.
"""
import math
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSlider, QStackedWidget, QVBoxLayout, QWidget,
)

import keys
from audio_engine import AudioEngine
from dialogs import AddSoundDialog, HotkeyDialog, HotkeysListDialog, SettingsDialog
from hotkey_manager import HotkeyManager
from sound_manager import SoundManager
from theme import MINT

ALL_CATEGORIES = "Все категории"
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
SPONSORS_DIR = APP_DIR / "assets" / "sponsors"      # рядом с .py или рядом с .exe

CARD_HEIGHT_MAIN = 142          # карточка с перемоткой, циклом и громкостью
CARD_HEIGHT_LIBRARY = 92        # карточка библиотеки — без регуляторов
MIN_ROWS = 4                    # минимум пустых карточек вниз (чтобы было что листать)


def format_time(seconds: float) -> str:
    """Секунды → «м:сс»."""
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class NoWheelSlider(QSlider):
    """Слайдер, не перехватывающий колесо мыши: колесо продолжает прокручивать карточки."""

    def wheelEvent(self, event):
        event.ignore()


class SeekSlider(NoWheelSlider):
    """Полоса перемотки: клик в любом месте сразу перематывает звук."""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self._seek_to(event.position().x())
            self.sliderPressed.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self._seek_to(event.position().x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isSliderDown():
            self.setSliderDown(False)
            self.sliderReleased.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _seek_to(self, x: float) -> None:
        ratio = max(0.0, min(1.0, x / max(1, self.width())))
        value = self.minimum() + round(ratio * (self.maximum() - self.minimum()))
        self.setSliderPosition(int(value))


class ElidedLabel(QLabel):
    """QLabel, обрезающий длинный текст многоточием и показывающий полный текст в подсказке."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full = text
        self.setToolTip(text)

    def set_full_text(self, text: str) -> None:
        """Устанавливает полный текст и обрезает его по ширине."""
        self._full = text
        self.setToolTip(text)
        self._update_elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elide()

    def _update_elide(self) -> None:
        width = max(10, self.width())
        elided = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, width)
        if elided != self.text():
            self.setText(elided)


class CardScrollArea(QScrollArea):
    """Область со списком карточек: прокрутка колесом «по пикселям», без горизонтальной полосы."""

    PIXELS_PER_NOTCH = 90

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.verticalScrollBar().setSingleStep(30)

    def wheelEvent(self, event):
        bar = self.verticalScrollBar()
        if bar.maximum() <= 0:
            event.ignore()
            return
        angle = event.angleDelta().y()
        pixels = event.pixelDelta().y()
        if angle:
            step = self.PIXELS_PER_NOTCH * angle / 120
        elif pixels:
            step = pixels
        else:
            super().wheelEvent(event)
            return
        bar.setValue(bar.value() - int(step))
        event.accept()


class CategoryButton(QPushButton):
    """Кнопка «Все категории ▼» с выпадающим меню."""
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("category")
        self._items = [ALL_CATEGORIES]
        self._current = ALL_CATEGORIES
        self.clicked.connect(self._open_menu)
        self._update_text()

    def currentText(self) -> str:
        """Возвращает выбранную категорию."""
        return self._current

    def set_items(self, items: list[str]):
        """Задаёт список категорий для выпадающего меню."""
        self._items = items
        if self._current not in items:
            self._current = ALL_CATEGORIES
        self._update_text()

    def _update_text(self):
        self.setText(f"{self._current}  ▼")

    def _open_menu(self):
        menu = QMenu(self)
        for item in self._items:
            menu.addAction(item, lambda value=item: self._choose(value))
        menu.exec(self.mapToGlobal(QPoint(0, self.height())))

    def _choose(self, value: str):
        self._current = value
        self._update_text()
        self.changed.emit()


class Logo(QWidget):
    """Логотип: мятный квадрат с белыми дугами. Клик — на главный экран."""
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(96, 96)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(MINT))
        p.drawRoundedRect(self.rect(), 6, 6)
        pen = QPen(QColor("white"), 9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = 26, 70                       # центр дуг — левый нижний угол
        for r in (14, 31, 48):
            p.drawArc(cx - r, cy - r, 2 * r, 2 * r, 0 * 16, 90 * 16)
        p.drawPoint(cx, cy)


class SoundCard(QFrame):
    """Карточка звука.

    На главном экране (controls=True) внутри карточки есть перемотка,
    кнопка зацикливания и громкость. sound=None — пустой слот.
    """
    clicked = pyqtSignal(str)                 # sound_id ('' для пустого слота)
    context_requested = pyqtSignal(str, QPoint)
    seek_requested = pyqtSignal(str, float)   # sound_id, доля 0..1
    loop_toggled = pyqtSignal(str, bool)
    volume_changed = pyqtSignal(str, float)   # живое превью громкости
    volume_committed = pyqtSignal(str, float) # громкость зафиксирована

    def __init__(self, sound=None, controls=False, show_hotkey=True):
        super().__init__()
        self.sound_id = sound.id if sound else ""
        self.sound = sound
        self.card_controls = controls
        self.controls = bool(controls and sound is not None)
        self.setObjectName("card")
        self.setProperty("playing", False)
        self.setProperty("empty", sound is None)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(CARD_HEIGHT_MAIN if controls else CARD_HEIGHT_LIBRARY)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._duration = 0.0
        self._dragging = False

        self.icon = QLabel("▶")
        self.icon.setObjectName("cardIcon")
        self.icon.setFixedSize(38, 38)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text = "..." if sound is None else sound.name
        if sound is not None and sound.is_loop and not self.controls:
            text += "  ⟲"
        self.name = ElidedLabel(text)
        self.name.setObjectName("cardName")
        self.name.setMinimumWidth(10)
        self.name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.hotkey_badge = None
        self.loop_btn = None
        self.time_cur = None
        self.time_total = None
        self.seek = None
        self.vol_icon = None
        self.vol = None
        self.vol_value = None

        self._build_layout(sound, show_hotkey)

    # ----------------------------------------------------------- построение
    def _build_layout(self, sound, show_hotkey: bool) -> None:
        grid = QGridLayout(self)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(1, 1)

        if self.controls:
            self._build_controls(grid, sound, show_hotkey)
            return

        grid.addWidget(self.icon, 0, 0, 2, 1, Qt.AlignmentFlag.AlignVCenter)
        if sound is not None and show_hotkey and sound.hotkey:
            badge = QLabel(keys.pretty(sound.hotkey))
            badge.setObjectName("badge")
            self.hotkey_badge = badge
            grid.addWidget(self.name, 0, 1, Qt.AlignmentFlag.AlignBottom)
            grid.addWidget(badge, 1, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        else:
            grid.addWidget(self.name, 0, 1, 2, 1, Qt.AlignmentFlag.AlignVCenter)

    def _build_controls(self, grid: QGridLayout, sound, show_hotkey: bool) -> None:
        self.loop_btn = QPushButton("⟲")
        self.loop_btn.setObjectName("loop")
        self.loop_btn.setCheckable(True)
        self.loop_btn.setChecked(sound.is_loop)
        self.loop_btn.setFixedSize(24, 24)
        self.loop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.loop_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.loop_btn.setToolTip("Зациклить звук")
        self.loop_btn.toggled.connect(self._on_loop_toggled)

        self.time_cur = QLabel("0:00")
        self.time_cur.setObjectName("cardTime")
        self.time_cur.setFixedWidth(34)
        self.time_total = QLabel("--:--")
        self.time_total.setObjectName("cardTime")
        self.time_total.setFixedWidth(34)
        self.time_total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.seek = SeekSlider(Qt.Orientation.Horizontal)
        self.seek.setObjectName("seek")
        self.seek.setRange(0, 1000)
        self.seek.setSingleStep(5)
        self.seek.setPageStep(50)
        self.seek.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.seek.setToolTip("Перемотка")
        self.seek.valueChanged.connect(self._on_seek_value)
        self.seek.sliderPressed.connect(self._on_seek_pressed)
        self.seek.sliderReleased.connect(self._on_seek_released)

        self.vol_icon = QLabel("🔊")
        self.vol_icon.setObjectName("cardVol")
        self.vol = NoWheelSlider(Qt.Orientation.Horizontal)
        self.vol.setObjectName("volume")
        self.vol.setRange(0, 100)
        self.vol.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.vol.setToolTip("Громкость звука")
        self.vol_value = QLabel("100%")
        self.vol_value.setObjectName("cardTime")
        self.vol_value.setFixedWidth(34)
        self.vol_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.vol.valueChanged.connect(self._on_volume)
        self.vol.sliderReleased.connect(self._on_volume_released)
        self.set_volume(sound.volume)

        grid.addWidget(self.icon, 0, 0, 2, 1, Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.name, 0, 1, Qt.AlignmentFlag.AlignBottom)
        grid.addWidget(self.loop_btn, 0, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        if show_hotkey and sound.hotkey:
            badge = QLabel(keys.pretty(sound.hotkey))
            badge.setObjectName("badge")
            self.hotkey_badge = badge
            grid.addWidget(badge, 1, 1, 1, 2, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        grid.addWidget(self.time_cur, 2, 0)
        grid.addWidget(self.seek, 2, 1)
        grid.addWidget(self.time_total, 2, 2)
        grid.setRowMinimumHeight(2, 18)
        grid.addWidget(self.vol_icon, 3, 0)
        grid.addWidget(self.vol, 3, 1)
        grid.addWidget(self.vol_value, 3, 2)

    # ------------------------------------------------------------- события
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.sound_id)
        elif event.button() == Qt.MouseButton.RightButton and self.sound_id:
            self.context_requested.emit(self.sound_id, event.globalPosition().toPoint())

    def _on_loop_toggled(self, state: bool) -> None:
        self.loop_toggled.emit(self.sound_id, state)

    def _on_seek_value(self, value: int) -> None:
        if self._duration > 0:
            self.time_cur.setText(format_time(self._duration * value / self.seek.maximum()))

    def _on_seek_pressed(self) -> None:
        self._dragging = True

    def _on_seek_released(self) -> None:
        self._dragging = False
        self.seek_requested.emit(self.sound_id, self.seek.value() / self.seek.maximum())

    def _on_volume(self, value: int) -> None:
        if self.vol_icon is not None:
            self.vol_icon.setText("🔇" if value == 0 else ("🔈" if value < 50 else "🔊"))
        if self.vol_value is not None:
            self.vol_value.setText(f"{value}%")
        self.volume_changed.emit(self.sound_id, value / 100)

    def _on_volume_released(self) -> None:
        self.volume_committed.emit(self.sound_id, self.vol.value() / 100)

    # ------------------------------------------------------------- состояние
    def set_playing(self, playing: bool) -> None:
        """Показывает состояние воспроизведения карточки."""
        self.setProperty("playing", playing)
        self.icon.setText("■" if playing else "▶")
        self.style().unpolish(self)
        self.style().polish(self)
        if not playing and self.controls:
            self.seek.setValue(0)
            self.time_cur.setText("0:00")
            self._dragging = False

    def set_duration(self, duration: float) -> None:
        """Устанавливает длительность звука для полосы перемотки."""
        self._duration = max(0.0, duration)
        if self.time_total is not None:
            self.time_total.setText(
                format_time(round(self._duration)) if self._duration > 0 else "--:--")

    def set_progress(self, position: float, duration: float) -> None:
        """Обновляет позицию воспроизведения на карточке."""
        if duration > 0:
            self.set_duration(duration)
        if not self.controls or self._dragging:
            return
        value = 0
        if self._duration > 0:
            value = int(round(position / self._duration * self.seek.maximum()))
        self.seek.blockSignals(True)
        self.seek.setValue(max(0, min(self.seek.maximum(), value)))
        self.seek.blockSignals(False)
        self.time_cur.setText(format_time(position))

    def set_volume(self, volume: float) -> None:
        """Показать громкость звука (0..1) без сигнала об изменении."""
        if self.vol is None:
            return
        value = max(0, min(100, int(round(volume * 100))))
        self.vol.blockSignals(True)
        self.vol.setValue(value)
        self.vol.blockSignals(False)
        self._on_volume(value)

    def update_from_sound(self, sound) -> None:
        """Обновить карточку после изменения модели без пересборки сетки."""
        self.sound = sound
        if self.controls:
            self.loop_btn.blockSignals(True)
            self.loop_btn.setChecked(sound.is_loop)
            self.loop_btn.blockSignals(False)
            self.set_volume(sound.volume)
        else:
            text = sound.name + ("  ⟲" if sound.is_loop else "")
            self.name.set_full_text(text)


class SoundsPage(QWidget):
    """Экран со списком звуков. library=False — главный экран, True — «Библиотека»."""
    add_requested = pyqtSignal()
    stop_all_requested = pyqtSignal()
    library_requested = pyqtSignal()
    home_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    card_clicked = pyqtSignal(str)
    context_requested = pyqtSignal(str, QPoint)
    seek_requested = pyqtSignal(str, float)
    loop_toggled = pyqtSignal(str, bool)
    volume_changed = pyqtSignal(str, float)
    volume_committed = pyqtSignal(str, float)
    master_volume_changed = pyqtSignal(int)
    master_volume_committed = pyqtSignal(int)

    def __init__(self, library: bool):
        super().__init__()
        self.setObjectName("page")
        self.library = library
        self.columns = 5 if library else 4
        self.card_height = CARD_HEIGHT_LIBRARY if library else CARD_HEIGHT_MAIN
        self.cards: dict[str, SoundCard] = {}
        self.now_rows: dict[str, QFrame] = {}
        self._sounds, self._is_playing = [], (lambda sid: False)
        self._durations: dict[str, float] = {}
        self._rows = 0

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(120)
        self._resize_timer.timeout.connect(self._sync_grid)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        main = QVBoxLayout()
        main.setContentsMargins(16, 12, 16, 8)
        main.setSpacing(12)
        root.addLayout(main, 1)
        self._build_top(main)
        self._build_body(main)
        if not library:
            self._build_sponsors(main)

    # ----------------------------------------------------------- построение
    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(120)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(4, 8, 4, 8)
        logo = Logo()
        logo.clicked.connect(self.home_requested)
        sl.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        sl.addStretch()
        self.total_label = QLabel()
        self.total_label.setObjectName("total")
        sl.addWidget(self.total_label)
        return side

    def _make_filters(self):
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("⌕  Поиск звуков....")
        self.search.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.search.textChanged.connect(lambda _text: self.render())
        self.search.returnPressed.connect(self.search.clearFocus)
        self.category = CategoryButton()
        self.category.changed.connect(self.render)

    def _build_top(self, main: QVBoxLayout):
        add_btn = QPushButton("+ Добавить звук")
        add_btn.setObjectName("green")
        add_btn.clicked.connect(self.add_requested)
        gear = QPushButton("⚙")
        gear.setObjectName("gear")
        gear.setToolTip("Настройки")
        gear.clicked.connect(self.settings_requested)
        self._make_filters()

        top = QHBoxLayout()
        top.addWidget(add_btn)
        if self.library:
            home = QPushButton("← Главная")
            home.setObjectName("blue")
            home.clicked.connect(self.home_requested)
            top.addWidget(home)
            top.addSpacing(8)
            top.addWidget(self.search, 1)
            top.addWidget(self.category)
            top.addSpacing(8)
            top.addWidget(gear)
            main.addLayout(top)
        else:
            stop = QPushButton("■ Стоп все")
            stop.setObjectName("red")
            stop.clicked.connect(self.stop_all_requested)
            lib = QPushButton("Библиотека")
            lib.setObjectName("blue")
            lib.clicked.connect(self.library_requested)
            top.addWidget(stop)
            top.addWidget(lib)
            top.addStretch()
            top.addWidget(gear)
            main.addLayout(top)
            filters = QHBoxLayout()
            filters.setSpacing(8)
            self.search.setMaximumWidth(460)
            filters.addWidget(self.search, 1)
            filters.addWidget(self.category)
            filters.addStretch(1)
            self._build_master_volume(filters)
            main.addLayout(filters)

    def _build_master_volume(self, filters: QHBoxLayout) -> None:
        """Общая громкость прямо на главном экране."""
        self.master_label = QLabel("🔊 Громкость")
        self.master_label.setObjectName("masterLabel")
        self.master = NoWheelSlider(Qt.Orientation.Horizontal)
        self.master.setObjectName("master")
        self.master.setRange(0, 100)
        self.master.setFixedWidth(140)
        self.master.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.master.setToolTip("Общая громкость всех звуков")
        self.master_value = QLabel("70%")
        self.master_value.setObjectName("masterValue")
        self.master_value.setFixedWidth(38)
        self.master.valueChanged.connect(self._on_master_volume)
        self.master.sliderReleased.connect(
            lambda: self.master_volume_committed.emit(self.master.value()))
        filters.addWidget(self.master_label)
        filters.addWidget(self.master)
        filters.addWidget(self.master_value)

    def _build_body(self, main: QVBoxLayout):
        body = QHBoxLayout()
        host = QWidget()
        outer = QVBoxLayout(host)
        outer.setContentsMargins(0, 0, 0, 0)
        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        for c in range(self.columns):
            self.grid.setColumnStretch(c, 1)
        outer.addLayout(self.grid)
        outer.addStretch()
        self.scroll = CardScrollArea()
        self.scroll.setWidget(host)
        body.addWidget(self.scroll, 1)

        if not self.library:
            panel = QFrame()
            panel.setObjectName("nowPanel")
            panel.setFixedWidth(230)
            pl = QVBoxLayout(panel)
            title = QLabel("Сейчас играет:")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pl.addWidget(title)
            self.now_layout = QVBoxLayout()
            pl.addLayout(self.now_layout)
            pl.addStretch()
            body.addWidget(panel)
        main.addLayout(body, 1)

    def _build_sponsors(self, main: QVBoxLayout):
        logos = sorted(SPONSORS_DIR.glob("*.png")) if SPONSORS_DIR.exists() else []
        if not logos:
            return
        row = QHBoxLayout()
        row.addWidget(QLabel("Наши спонсоры:"))
        for path in logos:
            lbl = QLabel()
            lbl.setPixmap(QPixmap(str(path)).scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            row.addWidget(lbl)
        row.addStretch()
        main.addLayout(row)

    # ------------------------------------------------------------ сетка
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_resize_timer"):
            self._resize_timer.start()

    def _visible_rows(self) -> int:
        """Сколько рядов карточек помещается в окно (+1 ряд, чтобы всегда было что листать)."""
        viewport_h = self.scroll.viewport().height() if hasattr(self, "scroll") else 0
        if viewport_h <= 0:
            return MIN_ROWS
        row_h = self.card_height + self.grid.spacing()
        return max(MIN_ROWS, math.ceil(viewport_h / row_h) + 1)

    def _desired_columns(self) -> int:
        """Число колонок под ширину окна: на узком экране регуляторам карточки нужно место."""
        viewport_w = self.scroll.viewport().width() if hasattr(self, "scroll") else 0
        if self.library:
            if viewport_w and viewport_w < 760:
                return 3
            if viewport_w and viewport_w < 1080:
                return 4
            return 5
        if viewport_w and viewport_w < 860:
            return 3
        return 4

    def _sync_grid(self):
        columns = self._desired_columns()
        if columns != self.columns or self._visible_rows() != self._rows:
            self.columns = columns
            self.render()

    def _filtered_sounds(self):
        text = self.search.text().strip().lower()
        cat = self.category.currentText()
        return [s for s in self._sounds
                if text in s.name.lower() and cat in ("", ALL_CATEGORIES, s.category)]

    # ------------------------------------------------------------ данные
    def set_categories(self, categories: list[str]):
        """Передаёт странице список доступных категорий."""
        self.category.set_items([ALL_CATEGORIES, *categories])

    def populate(self, sounds, is_playing):
        """Заполняет страницу звуками и перерисовывает сетку."""
        self._sounds, self._is_playing = sounds, is_playing
        self.total_label.setText(f"Всего звуков: {len(sounds)}")
        self.render()

    def render(self, preserve_scroll: bool = True):
        """Перестраивает сетку карточек с учётом фильтров и размера окна."""
        scrollbar = self.scroll.verticalScrollBar()
        old_value = scrollbar.value()

        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.cards.clear()

        shown = self._filtered_sounds()
        columns = self.columns
        rows = max(self._visible_rows(), math.ceil(len(shown) / columns))
        self._rows = rows
        for column in range(5):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        slots = rows * columns
        for i in range(slots):
            sound = shown[i] if i < len(shown) else None
            card = SoundCard(sound, controls=not self.library, show_hotkey=not self.library)
            card.clicked.connect(self.card_clicked)
            card.context_requested.connect(self.context_requested)
            if not self.library and sound is not None:
                card.seek_requested.connect(self.seek_requested)
                card.loop_toggled.connect(self.loop_toggled)
                card.volume_changed.connect(self.volume_changed)
                card.volume_committed.connect(self.volume_committed)
            if sound:
                self.cards[sound.id] = card
                card.set_playing(self._is_playing(sound.id))
                duration = self._durations.get(sound.id, 0.0)
                if duration > 0:
                    card.set_duration(duration)
            self.grid.addWidget(card, i // columns, i % columns)

        if preserve_scroll:
            QTimer.singleShot(0, lambda: scrollbar.setValue(min(old_value, scrollbar.maximum())))

    # ------------------------------------------------------------ обновления
    def set_duration(self, sound_id: str, duration: float) -> None:
        """Сохраняет и показывает длительность звука."""
        self._durations[sound_id] = duration
        card = self.cards.get(sound_id)
        if card is not None:
            card.set_duration(duration)

    def set_progress(self, sound_id: str, position: float, duration: float) -> None:
        """Передаёт позицию воспроизведения карточке звука."""
        if duration > 0:
            self._durations[sound_id] = duration
        card = self.cards.get(sound_id)
        if card is not None:
            card.set_progress(position, duration)

    def sync_sound(self, sound) -> None:
        """Обновляет карточку после изменения модели без пересборки сетки."""
        card = self.cards.get(sound.id)
        if card is not None:
            card.update_from_sound(sound)

    def set_master_volume(self, value: int) -> None:
        """Показывает общую громкость на главном экране."""
        if not hasattr(self, "master"):
            return
        self.master.blockSignals(True)
        self.master.setValue(int(value))
        self.master.blockSignals(False)
        self.master_value.setText(f"{int(value)}%")

    def _on_master_volume(self, value: int) -> None:
        self.master_value.setText(f"{value}%")
        self.master_volume_changed.emit(value)

    # ------------------------------------------------------ «Сейчас играет»
    def mark_started(self, sound_id: str, name: str, stop_callback):
        """Отмечает звук как играющий и добавляет его в «Сейчас играет»."""
        if sound_id in self.cards:
            self.cards[sound_id].set_playing(True)
        if self.library or sound_id in self.now_rows:
            return
        row = QFrame()
        row.setObjectName("nowRow")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(6, 2, 4, 2)
        rl.addWidget(ElidedLabel(name), 1)
        stop = QPushButton("■")
        stop.setObjectName("mini")
        stop.clicked.connect(lambda: stop_callback(sound_id))
        rl.addWidget(stop)
        self.now_layout.addWidget(row)
        self.now_rows[sound_id] = row

    def mark_finished(self, sound_id: str):
        """Снимает подсветку и убирает звук из «Сейчас играет»."""
        if sound_id in self.cards:
            self.cards[sound_id].set_playing(False)
        row = self.now_rows.pop(sound_id, None)
        if row is not None:
            row.hide()
            row.setParent(None)
            row.deleteLater()


class MainWindow(QMainWindow):
    """Главное окно приложения и контроллер взаимодействия компонентов."""
    def __init__(self, manager: SoundManager, engine: AudioEngine, hotkeys: HotkeyManager):
        super().__init__()
        self.manager, self.engine, self.hotkeys = manager, engine, hotkeys
        self.setWindowTitle("Soundboard")
        self.resize(1400, 820)
        self.setMinimumSize(1050, 660)

        self.main_page = SoundsPage(library=False)
        self.library_page = SoundsPage(library=True)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.main_page)
        self.pages.addWidget(self.library_page)
        self.setCentralWidget(self.pages)

        for page in (self.main_page, self.library_page):
            page.add_requested.connect(self.add_sound)
            page.home_requested.connect(self.show_main)
            page.settings_requested.connect(self.open_settings)
            page.card_clicked.connect(self.on_card_clicked)
            page.context_requested.connect(self.show_context_menu)
            page.seek_requested.connect(self.seek_sound)
            page.loop_toggled.connect(self.set_sound_loop)
            page.volume_changed.connect(self.preview_sound_volume)
            page.volume_committed.connect(self.commit_sound_volume)
        self.main_page.stop_all_requested.connect(self.engine.stop_all)
        self.main_page.library_requested.connect(self.show_library)
        self.main_page.master_volume_changed.connect(self.preview_master_volume)
        self.main_page.master_volume_committed.connect(self.commit_master_volume)

        engine.started.connect(self.on_started)
        engine.finished.connect(self.on_finished)
        engine.progress.connect(self.on_progress)
        engine.error.connect(lambda msg: self.statusBar().showMessage(msg, 5000))
        manager.changed.connect(self.refresh)
        hotkeys.pressed.connect(self.on_global_key)

        # Длительности звуков догружаются по одной, чтобы не подвешивать запуск.
        self._duration_queue: list = []
        self._duration_timer = QTimer(self)
        self._duration_timer.setInterval(20)
        self._duration_timer.timeout.connect(self._load_next_duration)

        self.apply_settings()
        self.refresh()

    # ------------------------------------------------------------ экраны
    def show_main(self):
        """Переключает на главный экран."""
        self.pages.setCurrentWidget(self.main_page)

    def show_library(self):
        """Переключает на экран «Библиотека»."""
        self.pages.setCurrentWidget(self.library_page)

    def refresh(self):
        """Обновляет обе страницы по данным менеджера библиотеки."""
        categories = self.manager.categories()
        for page in (self.main_page, self.library_page):
            page.set_categories(categories)
            page.populate(self.manager.sounds, self.engine.is_playing)
        for sound in self.manager.sounds:
            duration = self.engine.duration(sound.id)
            if duration > 0:
                self.main_page.set_duration(sound.id, duration)
                self.library_page.set_duration(sound.id, duration)
        self._queue_durations()

    # ------------------------------------------------- длительности звуков
    def _queue_durations(self):
        missing = [s for s in self.manager.sounds if self.engine.duration(s.id) <= 0]
        self._duration_queue = missing
        if missing:
            if not self._duration_timer.isActive():
                self._duration_timer.start()
        else:
            self._duration_timer.stop()

    def _load_next_duration(self):
        if not self._duration_queue:
            self._duration_timer.stop()
            return
        sound = self._duration_queue.pop(0)
        duration = self.engine.load_duration(sound)
        if duration > 0:
            for page in (self.main_page, self.library_page):
                page.set_duration(sound.id, duration)
        if not self._duration_queue:
            self._duration_timer.stop()

    # --------------------------------------------------------------- воспроизведение
    def toggle(self, sound_id: str):
        """Запускает или останавливает звук по его идентификатору."""
        sound = self.manager.get(sound_id)
        if not sound:
            return
        if self.engine.is_playing(sound_id):
            self.engine.stop(sound_id)
        else:
            self.engine.play(sound)

    def on_card_clicked(self, sound_id: str):
        """Обрабатывает клик по карточке звука или пустому слоту."""
        if sound_id:
            self.toggle(sound_id)
        else:
            self.add_sound()

    def on_started(self, sound_id: str):
        """Обрабатывает сигнал начала воспроизведения."""
        sound = self.manager.get(sound_id)
        name = sound.name if sound else ""
        for page in (self.main_page, self.library_page):
            page.mark_started(sound_id, name, self.engine.stop)

    def on_finished(self, sound_id: str):
        """Обрабатывает сигнал завершения воспроизведения."""
        for page in (self.main_page, self.library_page):
            page.mark_finished(sound_id)

    def on_progress(self, sound_id: str, position: float, duration: float):
        """Передаёт позицию воспроизведения в карточки звуков."""
        for page in (self.main_page, self.library_page):
            page.set_progress(sound_id, position, duration)

    # ------------------------------------------------ регуляторы на карточке
    def seek_sound(self, sound_id: str, fraction: float):
        """Перематывает звук на заданную долю длительности."""
        sound = self.manager.get(sound_id)
        if sound:
            self.engine.seek(sound, fraction)

    def set_sound_loop(self, sound_id: str, state: bool):
        """Включает или выключает зацикливание звука."""
        sound = self.manager.get(sound_id)
        if not sound:
            return
        self.manager.update(sound_id, silent=True, is_loop=state)
        self.engine.set_loop(sound_id, state)
        for page in (self.main_page, self.library_page):
            page.sync_sound(sound)

    def preview_sound_volume(self, sound_id: str, volume: float):
        """Применяет громкость звука без сохранения в файл."""
        self.engine.set_sound_volume(sound_id, volume)

    def commit_sound_volume(self, sound_id: str, volume: float):
        """Сохраняет громкость звука в конфигурацию."""
        self.engine.set_sound_volume(sound_id, volume)
        self.manager.update(sound_id, silent=True, volume=volume)

    def preview_master_volume(self, percent: int):
        """Применяет общую громкость без сохранения в файл."""
        self.engine.set_master_volume(percent)

    def commit_master_volume(self, percent: int):
        """Сохраняет общую громкость в настройки."""
        self.engine.set_master_volume(percent)
        self.manager.set_settings(master_volume=percent)

    # --------------------------------------------------------------- клавиши
    def handle_key(self, key: str):
        """Обрабатывает нажатие горячей клавиши (Esc — паника)."""
        if key == "esc":
            self.engine.stop_all()            # Esc — «паника»
            return
        sound = self.manager.find_by_hotkey(key)
        if sound:
            self.toggle(sound.id)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = keys.from_qt_event(event)
        if key:
            self.handle_key(key)
        else:
            super().keyPressEvent(event)

    def on_global_key(self, key: str):
        # когда окно активно, клавиши обрабатывает keyPressEvent
        if QApplication.activeWindow() is None:
            self.handle_key(key)

    # ---------------------------------------------------------------- действия
    def add_sound(self):
        """Открывает диалог добавления звука."""
        dlg = AddSoundDialog(self.manager, self)
        if dlg.exec():
            self.manager.add(**dlg.values())

    def change_hotkey(self, sound_id: str):
        """Открывает диалог назначения горячей клавиши."""
        sound = self.manager.get(sound_id)
        if not sound:
            return
        dlg = HotkeyDialog(self.manager, sound, self)
        if dlg.exec():
            self.manager.update(sound_id, hotkey=dlg.key())

    def rename_sound(self, sound_id: str):
        """Переименовывает звук через диалог ввода."""
        sound = self.manager.get(sound_id)
        if not sound:
            return
        name, ok = QInputDialog.getText(self, "Переименовать", "Название звука:", text=sound.name)
        if ok and name.strip():
            self.manager.update(sound_id, name=name.strip())

    def change_volume(self, sound_id: str):
        """Меняет громкость звука через диалог ввода."""
        sound = self.manager.get(sound_id)
        if not sound:
            return
        value, ok = QInputDialog.getInt(self, "Громкость звука", "Громкость, %:",
                                        round(sound.volume * 100), 0, 100)
        if ok:
            self.manager.update(sound_id, volume=value / 100)
            self.engine.set_sound_volume(sound_id, value / 100)

    def toggle_loop(self, sound_id: str, state: bool):
        """Переключает зацикливание звука (обёртка для контекстного меню)."""
        self.set_sound_loop(sound_id, state)

    def remove_sound(self, sound_id: str):
        """Удаляет звук из библиотеки после подтверждения."""
        sound = self.manager.get(sound_id)
        if not sound:
            return
        answer = QMessageBox.question(self, "Удаление", f"Удалить звук «{sound.name}» из библиотеки?")
        if answer == QMessageBox.StandardButton.Yes:
            self.engine.invalidate(sound_id)
            self.manager.remove(sound_id)

    def show_context_menu(self, sound_id: str, pos: QPoint):
        """Показывает контекстное меню карточки звука."""
        sound = self.manager.get(sound_id)
        if not sound:
            return
        menu = QMenu(self)
        menu.addAction("Назначить клавишу…", lambda: self.change_hotkey(sound_id))
        menu.addAction("Переименовать…", lambda: self.rename_sound(sound_id))
        menu.addAction("Громкость…", lambda: self.change_volume(sound_id))
        loop = menu.addAction("Зацикливать")
        loop.setCheckable(True)
        loop.setChecked(sound.is_loop)
        loop.toggled.connect(lambda state: self.toggle_loop(sound_id, state))
        menu.addSeparator()
        menu.addAction("Удалить", lambda: self.remove_sound(sound_id))
        menu.exec(pos)

    def open_settings(self):
        """Открывает окно настроек."""
        def to_hotkeys():
            HotkeysListDialog(self, dlg).exec()

        dlg = SettingsDialog(self.manager.settings, to_hotkeys, self)
        if dlg.exec():
            self.manager.set_settings(**dlg.values())
            self.apply_settings()

    def apply_settings(self):
        """Применяет настройки к движку и горячим клавишам."""
        s = self.manager.settings
        self.engine.set_master_volume(s["master_volume"])
        self.engine.allow_overlap = s["allow_overlap"]
        self.engine.loop_all = s["loop_all"]
        self.main_page.set_master_volume(s["master_volume"])
        if s["global_hotkeys"]:
            if not self.hotkeys.start():
                self.statusBar().showMessage("Глобальные клавиши недоступны (не установлен pynput)", 5000)
        else:
            self.hotkeys.stop()

    def closeEvent(self, event):
        self._duration_timer.stop()
        self.manager.save()
        self.hotkeys.stop()
        self.engine.shutdown()
        super().closeEvent(event)
