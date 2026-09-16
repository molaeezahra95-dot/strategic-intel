@echo off
setlocal
cd /d "%~dp0"
set "PROJECT_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" set "PROJECT_PYTHON=%CD%\..\finance-nav-dashboard\.venv\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" (
 echo Python environment missing. See _support\STATUS.md
 pause
 exit /b 1
)
"%PROJECT_PYTHON%" -X utf8 "%CD%\_support\start.py" %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" if not "%~1"=="--check" pause
exit /b %RESULT%
