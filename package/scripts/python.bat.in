@echo off
@REM ---------------------------------------------------------------------------
@REM This batch file is a launcher script designed to start Bookmark's interactive
@REM python interpreter. The script sets up a localized environment for the Python
@REM interpreter by specifying PYTHONHOME, PYTHONPATH, PYTHONSTARTUP, PATH, and 
@REM BOOKMARKS_ROOT variables.
@REM
@REM PYTHONHOME: This points to the root directory of the Python installation.
@REM PYTHONPATH: Specifies additional directories to add to the module search path.
@REM              Here, it includes 'core' and 'shared' directories relative to the
@REM              Python root directory.
@REM PYTHONSTARTUP: Points to a python script that is automatically executed every
@REM                 time the Python interpreter starts.
@REM PATH: Augments the existing PATH with the root directory and additional 'bin'
@REM       and 'DLLs' directories relative to the Python root directory.
@REM BOOKMARKS_ROOT: An application-specific variable representing the root
@REM                  directory of the application.
@REM
@REM At the end, it launches the Python interpreter from the root directory with 
@REM any command line arguments passed to the script.
@REM
@REM Usage: 
@REM To use this script, call it from the command line along with any command line
@REM arguments you would like to pass to the Python interpreter.
@REM 
@REM Note: The batch file must be in the same directory as the Python root directory 
@REM       to properly set up the environment variables.
@REM ---------------------------------------------------------------------------
@echo off

setlocal
for %%i in ("%~dp0.") do set "root=%%~fi"

set "PYTHONHOME=%root%"
set "PYTHONPATH=%root%\core;%root%\shared"
set "PYTHONSTARTUP=%root%\.pythonstartup"
set "PATH=%root%;%root%\bin;%root%\DLLs;%PATH%"

set "BOOKMARKS_ROOT=%root%"

%root%\python.exe %*