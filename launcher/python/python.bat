@REM Use this launcher to start Bookmark's interactive python interpreter
@echo off

setlocal
for %%i in ("%~dp0.") do set "root=%%~fi"

set "PYTHONHOME=%root%"
set "PYTHONPATH=%root%\core;%root%\shared"
set "PYTHONSTARTUP=%root%\.pythonstartup"

set "BOOKMARKS_ROOT=%root%"
set "PATH=%root%;%root%\bin;%root%\DLLs;%PATH%"

%root%\python.exe

