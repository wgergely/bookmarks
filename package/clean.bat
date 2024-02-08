@echo off
echo Removing build directory...

if not exist build (
    echo Build directory does not exist. No action needed.
    exit /b 0
)

rd /s /q build
if errorlevel 1 (
    echo Error: Failed to remove build directory.
    exit /b 1
) else (
    echo Build directory removed successfully.
)

exit /b 0
