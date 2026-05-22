@echo off
taskkill /F /IM chrome.exe >/dev/null 2>&1
timeout /t 3 /nobreak >/dev/null
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\pc\AppData\Local\Google\Chrome\User Data"
