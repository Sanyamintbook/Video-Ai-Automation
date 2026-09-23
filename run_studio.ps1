# Olympiad AI Video Studio PowerShell Launcher
$pythonPath = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$scriptsPath = "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"

# Refresh current session PATH
$env:Path = "$pythonPath;$scriptsPath;$env:Path"

if (Test-Path $pythonPath) {
    & $pythonPath -m streamlit run app_ui.py
} else {
    py -3.12 -m streamlit run app_ui.py
}
