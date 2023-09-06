@echo off

:: Try to find the path to vswhere.exe
SET VSWHERE="C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"

:: Check if vswhere is available
IF NOT EXIST %VSWHERE% (
    echo Error: "vswhere.exe" not found. Please ensure you have Visual Studio 2017 or newer installed.
    exit /b 1
)

:: Use vswhere to find the latest VS installation with VC tools
FOR /F "tokens=*" %%i IN ('%VSWHERE% -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath') DO (
    SET VSPATH=%%i
)

IF NOT DEFINED VSPATH (
    echo Error: Suitable Visual Studio installation not found.
    exit /b 1
)

:: Construct path to vcvars64.bat using the found VS path
SET VCVARS64="%VSPATH%\VC\Auxiliary\Build\vcvars64.bat"

:: Check for vcvars64.bat existence
IF NOT EXIST %VCVARS64% (
    echo Error: "vcvars64.bat" not found in detected Visual Studio path.
    exit /b 1
)

call %VCVARS64%

:: Check for cmake
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
