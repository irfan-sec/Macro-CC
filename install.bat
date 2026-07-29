@echo off
echo ============================================
echo   Macro Recorder Pro — Quick Installer
echo ============================================
echo.

set "INSTALL_DIR=%APPDATA%\MacroRecorderPro"

echo Installing to: %INSTALL_DIR%
echo.

mkdir "%INSTALL_DIR%" 2>nul
mkdir "%INSTALL_DIR%\storage\macros" 2>nul
mkdir "%INSTALL_DIR%\assets" 2>nul

copy /y "dist\MacroRecorderPro.exe" "%INSTALL_DIR%\" >nul
copy /y "assets\icon.ico" "%INSTALL_DIR%\assets\" >nul

echo Creating Desktop shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\Macro Recorder Pro.lnk'); $s.TargetPath = '%INSTALL_DIR%\MacroRecorderPro.exe'; $s.IconLocation = '%INSTALL_DIR%\assets\icon.ico'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Save()"

echo.
echo ============================================
echo   Done! Shortcut created on Desktop.
echo   Install location: %INSTALL_DIR%
echo ============================================
echo.
pause
