@echo off

@REM Check for cmake
where cmake >nul 2>nul
IF ERRORLEVEL 1 (
    echo Error: cmake is not installed or not in the PATH.
    exit /b 1
)

:: Get the Visual Studio version
if defined VisualStudioVersion (
    set VS_VERSION=%VisualStudioVersion%
) else (
    echo Visual Studio environment not set up!
    exit /b 1
)

:: Get the Visual Studio name for CMake
if "%VS_VERSION%"=="16.0" (
    set VS_NAME="Visual Studio 16 2019"
) else (
    echo Unsupported Visual Studio version!
    exit /b 1
)

:: Get the architecture
if defined VSCMD_ARG_TGT_ARCH (
    set VS_ARCH=%VSCMD_ARG_TGT_ARCH%
) else (
    echo Architecture not set!
    exit /b 1
)

:: Print the values
echo VS_NAME: %VS_NAME%
echo VS_ARCH: %VS_ARCH%

set "_script_dir=%~dp0"
:: Remove the trailing backslash
set "_script_dir=%_script_dir:~0,-1%"
echo The directory of the script is: %_script_dir%

:: Get the parent directory
for %%i in ("%_script_dir%") do set "_parent_dir=%%~dpi"

cmake ^
-S "%_script_dir%" ^
-B "%_script_dir%/build" ^
-G %VS_NAME% ^
-A %VS_ARCH% ^
-DCMAKE_BUILD_TYPE=Release

@REM @REM Build dependencies
cmd /c msbuild.exe "%_script_dir%/build/Bookmarks.sln" -target:Build -property:Configuration=Release -property:Platform=%VS_ARCH% /m /nologo

@REM @REM Build pyside
cmd /c "%_script_dir%/build/packages/build-pyside.bat"

@REM @REM Build image util
cmd /c "%_script_dir%/build/build-imageutil.bat"

@REM Build application package
cmd /c "%_script_dir%/build/packages/build-package.bat"

@REM Build installer
mkdir "%_script_dir%/build/install"
for /d /r "%_script_dir%/build/package" %%G in (__pycache__) do (
    if exist "%%G" (
        echo Removing "%%G"
        rd /s /q "%%G"
    )
)
"%_script_dir%/build/packages/inno/ISCC.exe" /O"%_script_dir%/build/install" "%_script_dir%/build/install/installer.iss"