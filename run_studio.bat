@echo off
title Olympiad AI Video Studio
echo Starting Olympiad AI Video Studio...

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" -m streamlit run app_ui.py
) else (
    py -3.12 -m streamlit run app_ui.py
)

pause
