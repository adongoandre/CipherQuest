@echo off
rem ===========================================================================
rem  CipherQuest launcher
rem
rem  Starts the FastAPI backend and the Vite dev server, each in its own
rem  window, waits until they answer, then opens the site in your browser.
rem  Anything already running is left alone, so it is safe to double-click
rem  twice or to run it while the app is open.
rem ===========================================================================
setlocal EnableExtensions
title CipherQuest

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "API_URL=http://127.0.0.1:8000/api/v1/health"
set "WEB_URL=http://localhost:5173/"

rem ---- is this really the project folder? -----------------------------------
if not exist "%ROOT%\backend\.venv\Scripts\python.exe" goto no_venv
if not exist "%ROOT%\frontend\node_modules" goto no_modules

rem ---- curl ships with Windows 10+; without it we skip the health checks ---
set "CURL="
where curl >nul 2>&1
if not errorlevel 1 set "CURL=1"

rem =========================== backend ======================================
set "API_UP="
if not defined CURL goto start_api
curl -s -o nul --max-time 2 "%API_URL%" >nul 2>&1
if not errorlevel 1 set "API_UP=1"
if not defined API_UP goto start_api
echo API already running on http://127.0.0.1:8000
goto web_part

:start_api
echo Starting the API window...
start "CipherQuest API" /d "%ROOT%\backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
if not defined CURL goto web_part

echo Waiting for the API to answer...
set /a TRIES=0
:wait_api
curl -s -o nul --max-time 2 "%API_URL%" >nul 2>&1
if not errorlevel 1 goto api_ready
set /a TRIES+=1
if %TRIES% GEQ 30 goto api_slow
"%SystemRoot%\System32\timeout.exe" /t 1 /nobreak >nul 2>&1
goto wait_api

:api_slow
echo WARNING: the API did not answer within 30 seconds.
echo Open the "CipherQuest API" window to see the error.
goto web_part

:api_ready
echo API is up.

rem =========================== frontend =====================================
:web_part
set "WEB_UP="
if not defined CURL goto start_web
curl -s -o nul --max-time 2 "%WEB_URL%" >nul 2>&1
if not errorlevel 1 set "WEB_UP=1"
if not defined WEB_UP goto start_web
echo Web app already running on %WEB_URL%
goto open_browser

:start_web
echo Starting the web window...
start "CipherQuest Web" /d "%ROOT%\frontend" cmd /k "npm run dev"
if not defined CURL goto open_browser

echo Waiting for the web app to answer...
set /a TRIES=0
:wait_web
curl -s -o nul --max-time 2 "%WEB_URL%" >nul 2>&1
if not errorlevel 1 goto web_ready
set /a TRIES+=1
if %TRIES% GEQ 40 goto web_slow
"%SystemRoot%\System32\timeout.exe" /t 1 /nobreak >nul 2>&1
goto wait_web

:web_slow
echo WARNING: the web app did not answer within 40 seconds.
echo Open the "CipherQuest Web" window to see the error.
goto open_browser

:web_ready
echo Web app is up.

rem =========================== browser ======================================
:open_browser
start "" "%WEB_URL%"
echo.
echo CipherQuest is open at %WEB_URL%
echo Keep the "CipherQuest API" and "CipherQuest Web" windows open while playing.
echo Close those two windows to stop the application.
"%SystemRoot%\System32\timeout.exe" /t 3 /nobreak >nul 2>&1
exit /b 0

rem =========================== setup problems ===============================
:no_venv
echo Cannot find backend\.venv\Scripts\python.exe
echo The Python environment is missing. See README.md for the setup steps.
pause
exit /b 1

:no_modules
echo Cannot find frontend\node_modules
echo The web dependencies are missing. Run "npm install" in the frontend folder.
pause
exit /b 1
