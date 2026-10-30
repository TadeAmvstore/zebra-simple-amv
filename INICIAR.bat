@echo off
setlocal
cd /d "%~dp0"
if not exist "app.py" (
 echo ERROR: Extrae el ZIP completo antes de iniciar.
 pause
 exit /b 1
)
rem Python 3.13 is preferred for PyMuPDF binary compatibility on Windows.
set "PYEXE="
py -3.13 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3.13"
if not defined PYEXE (
 echo ERROR: Zebra Simple AMV requiere Python 3.13 de 64 bits.
 echo Descargalo desde https://www.python.org/downloads/
 echo Durante la instalacion, habilita Python Launcher.
 pause
 exit /b 1
)
%PYEXE% actualizar.py
%PYEXE% -m pip install --disable-pip-version-check Flask Pillow PyMuPDF
if errorlevel 1 (
 echo ERROR: No se pudieron instalar las dependencias.
 pause
 exit /b 1
)
%PYEXE% -c "import fitz,flask,PIL" >nul 2>&1
if errorlevel 1 (
 echo ERROR: PyMuPDF no pudo cargar. Verifica Python 3.13 de 64 bits.
 pause
 exit /b 1
)
%PYEXE% app.py
if errorlevel 1 pause
