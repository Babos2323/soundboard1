@echo off
rem Сборка HTML-документации Soundboard (Sphinx).
cd /d "%~dp0"

if exist "..\..\.venv\Scripts\python.exe" (
    set "PYTHON=..\..\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

%PYTHON% -m pip install -r requirements.txt
%PYTHON% -m sphinx -b html . ..\HTML
echo.
echo Готово: %~dp0..\HTML\index.html
pause
