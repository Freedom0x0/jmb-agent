@echo off
setlocal
rem jmb daily brief wrapper (Task Scheduler entry; schedule defined in D30)
set "JMB_ROOT=C:\Users\15532\Desktop\xj\jmb"
set "LOG_DIR=%LOCALAPPDATA%\jmb\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
cd /d "%JMB_ROOT%"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
(echo [brief-task] start %DATE:~0,10%)>> "%LOG_DIR%\brief-task.log"
"C:\Users\15532\AppData\Local\Programs\Python\Python313\Scripts\uv.exe" run jmb brief >> "%LOG_DIR%\brief-task.log" 2>&1
set "RC=%ERRORLEVEL%"
(echo [brief-task] exit %RC%)>> "%LOG_DIR%\brief-task.log"
exit /b %RC%
