@echo off
setlocal
cd /d "%~dp0"

set ARGS=--noconfirm --windowed --onefile --name VLCPlayer main.py

if exist "C:\Program Files\VideoLAN\VLC\libvlc.dll" (
  set ARGS=%ARGS% --add-binary "C:\Program Files\VideoLAN\VLC\libvlc.dll;."
  set ARGS=%ARGS% --add-binary "C:\Program Files\VideoLAN\VLC\libvlccore.dll;."
)

pyinstaller %ARGS%
echo Executable : dist\VLCPlayer.exe
