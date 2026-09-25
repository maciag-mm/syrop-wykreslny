@echo off
rem Buduje Syrop Wykreslny (exe + instalator). Wyniki w folderze "wynik".
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build\build.ps1"
pause
