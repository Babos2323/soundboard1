"""Конфигурация Sphinx для документации Soundboard."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / "Код"))

project = "Soundboard"
author = "Загайнов Никита Александрович, группа ИСП-341"
copyright = "2026, Загайнов Н. А."
release = "1.3"
version = "1.3"

language = "ru"
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
source_suffix = {".rst": "restructuredtext"}

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
]

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "member-order": "bysource",
    "undoc-members": False,
}
autodoc_typehints = "description"
autodoc_member_order = "bysource"
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

todo_include_todos = True

try:
    import sphinx_rtd_theme  # noqa: F401

    html_theme = "sphinx_rtd_theme"
    html_theme_options = {
        "navigation_depth": 4,
        "collapse_navigation": False,
        "sticky_navigation": True,
        "includehidden": True,
        "titles_only": False,
    }
except ImportError:  # запасной вариант, если тема не установлена
    html_theme = "alabaster"

html_title = "Soundboard — документация"
html_logo = "images/icon.png"
html_favicon = "images/icon.png"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_show_sourcelink = True
html_last_updated_fmt = "%d.%m.%Y"
htmlhelp_basename = "Soundboarddoc"

pygments_style = "friendly"


def _skip_pyqt_signals(app, what, name, obj, skip, options):
    """Не документировать объекты pyqtSignal (у них техническое описание)."""
    if type(obj).__name__ == "pyqtSignal":
        return True
    return None


def setup(app):
    app.connect("autodoc-skip-member", _skip_pyqt_signals)

