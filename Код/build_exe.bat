@echo off
rem Сборка Soundboard.exe. Запускать двойным кликом из папки проекта.
rem Если рядом (в ..\.venv) есть готовое окружение — используем его, иначе создаём своё.

if exist "..\.venv\Scripts\python.exe" (
    set "PYTHON=..\.venv\Scripts\python.exe"
) else (
    if not exist ".venv\Scripts\python.exe" (
        py -m venv .venv
    )
    set "PYTHON=.venv\Scripts\python.exe"
)

%PYTHON% -m pip install -r requirements.txt pyinstaller
%PYTHON% -m PyInstaller --noconfirm --clean --noconsole --onedir --name Soundboard --icon assets\icon.ico --add-data "assets\icon.png;assets" --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 main.py
echo.
echo Готово: dist\Soundboard\Soundboard.exe
echo Запускать нужно Soundboard.exe из этой папки (рядом лежит _internal). 
pause
