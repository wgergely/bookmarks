@echo off
@REM -----------------------------------------------------------
@REM Main build script for Bookmark's Windows distribution.

@REM This script is designed to be run from the Visual Studio Developer Command Prompt.
@REM It sets up the environment for the build and then calls cmake to generate the build
@REM project. The script then builds the project and packages the application into an
@REM installer.
@REM 
@REM Usage:
@REM 
@REM --clean: Cleans the existing build directory
@REM --configure: Configures the build project using cmake
@REM --build-libraries: Builds the project's binary dependencies
@REM --build-pyside: Builds PySide
@REM --build-imageutil: Builds imageutil
@REM --build-package: Builds the application package
@REM --build-installer: Builds the installer
@REM 
@REM Author: Gergely Wootsch, hello@gergely-wootsch.com
@REM -----------------------------------------------------------

@REM Implement the command line arguments. The inputs are not case sensitive and can be combined in any order.
@REM The script will not execute anything if no arguments are provided.
@REM The script will exit if any of the commands fail.

<--- Implement the command line arguments here --->




@REM -----------------------------------------------------------
@REM Find Visual Studio
SET VSWHERE="C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"

@REM Check if vswhere is available
IF NOT EXIST %VSWHERE% (
    echo Error: "vswhere.exe" not found. Please ensure you have Visual Studio 2017 or newer installed.
    exit /b %ERRORLEVEL%
)

@REM Use vswhere to find the latest VS installation with VC tools
FOR /F "tokens=*" %%i IN ('%VSWHERE% -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath') DO (
    SET VSPATH=%%i
)

IF NOT DEFINED VSPATH (
    echo Error: Suitable Visual Studio installation not found.
    exit /b %ERRORLEVEL%
)

@REM Construct path to vcvars64.bat using the found VS path
SET VCVARS64="%VSPATH%\VC\Auxiliary\Build\vcvars64.bat"

@REM Check for vcvars64.bat existence
IF NOT EXIST %VCVARS64% (
    echo Error: "vcvars64.bat" not found in detected Visual Studio path.
    exit /b %ERRORLEVEL%
)

call %VCVARS64%

@REM Get the Visual Studio version
if defined VisualStudioVersion (
    set VS_VERSION=%VisualStudioVersion%
) else (
    echo Visual Studio environment not set up!
    exit /b %ERRORLEVEL%
)

@REM Get the Visual Studio name for CMake
if "%VS_VERSION%"=="16.0" (
    set VS_NAME="Visual Studio 16 2019"
) else (
    echo Unsupported Visual Studio version!
    exit /b %ERRORLEVEL%
)

@REM Get the architecture
if defined VSCMD_ARG_TGT_ARCH (
    set VS_ARCH=%VSCMD_ARG_TGT_ARCH%
) else (
    echo Architecture not set!
    exit /b %ERRORLEVEL%
)

@REM Print the values
echo VS_NAME: %VS_NAME%
echo VS_ARCH: %VS_ARCH%


@REM -----------------------------------------------------------
@REM Check for cmake
where cmake >nul 2>nul
IF ERRORLEVEL 1 (
    echo Error: cmake is not installed or not in the PATH.
    exit /b %ERRORLEVEL%
)


@REM -----------------------------------------------------------
@REM Set up the build environment
set "PACKAGE_SOURCE_DIR=%~dp0"
@REM Remove the trailing backslash
set "PACKAGE_SOURCE_DIR=%PACKAGE_SOURCE_DIR:~0,-1%"

@REM Mount the build directory as a drive to shorten the generated paths
set "BUILD_DRIVE=B:"
set "BUILD_PACKAGES_DIR=%BUILD_DRIVE%/packages"

subst %BUILD_DRIVE% "%PACKAGE_SOURCE_DIR%/build"

echo PACKAGE_SOURCE_DIR=%PACKAGE_SOURCE_DIR%

@REM Get the parent directory
for %%i in ("%PACKAGE_SOURCE_DIR%") do set "_parent_dir=%%~dpi"


@REM -----------------------------------------------------------
@REM Clean existing build
if EXIST "%BUILD_DRIVE%/build" (
    echo Cleaning existing build...
    rmdir "%BUILD_DRIVE%/build" /S /Q
)

@REM -----------------------------------------------------------
@REM Configure build project
cmake ^
-S "%PACKAGE_SOURCE_DIR%" ^
-B "%BUILD_DRIVE%" ^
-G %VS_NAME% ^
-A %VS_ARCH% ^
-DCMAKE_BUILD_TYPE=Release

IF ERRORLEVEL 1 (
    echo Failed to configure build project.
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)

@REM -----------------------------------------------------------
@REM Build project's binary dependencies
cmd /c msbuild.exe "B:/Bookmarks.sln" -target:Build -property:Configuration=Release -property:Platform=%VS_ARCH% /m /nologo

IF ERRORLEVEL 1 (
    echo Error: Failed to build Bookmarks.sln
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)

@REM -----------------------------------------------------------
@REM Build pyside
if NOT EXIST "%BUILD_PACKAGES_DIR%/scripts/build-pyside.bat" (
    echo Error: "%BUILD_PACKAGES_DIR%/scripts/build-pyside.bat" not found.
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)
cmd /c "%BUILD_PACKAGES_DIR%/scripts/build-pyside.bat"
IF ERRORLEVEL 1 (
    echo PySide encountered errors
    echo %ERRORLEVEL%
    echo Continuing build...
)

@REM Build imageutil
if NOT EXIST "%BUILD_PACKAGES_DIR%/scripts/build-imageutil.bat" (
    echo Error: "%BUILD_PACKAGES_DIR%/scripts/build-imageutil.bat" not found.
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)
cmd /c "%BUILD_PACKAGES_DIR%/scripts/build-imageutil.bat"
IF ERRORLEVEL 1 (
    echo Error: Failed to build imageutil
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)

@REM Build application package
if NOT EXIST "%BUILD_PACKAGES_DIR%/scripts/build-package.bat" (
    echo Error: "%BUILD_PACKAGES_DIR%/scripts/build-package.bat" not found.
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)
cmd /c "%BUILD_PACKAGES_DIR%/scripts/build-package.bat"
IF ERRORLEVEL 1 (
    echo Error: Failed to build package
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)

@REM Build installer
if NOT EXIST "%BUILD_PACKAGES_DIR%/inno/ISCC.exe" (
    echo Error: "%BUILD_PACKAGES_DIR%/inno/ISCC.exe" not found.
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)
mkdir "B:/install"
for /d /r "B:/package" %%G in (__pycache__) do (
    if exist "%%G" (
        echo Removing "%%G"
        rd /s /q "%%G"
    )
)
"%BUILD_PACKAGES_DIR%/inno/ISCC.exe" /O"B:/install" "B:/install/installer.iss"

IF ERRORLEVEL 1 (
    echo Error: Failed to build installer
    subst %BUILD_DRIVE% /D
    exit /b %ERRORLEVEL%
)

subst %BUILD_DRIVE% /D

echo.
echo Build completed.
echo Installer saved to:
echo %PACKAGE_SOURCE_DIR%/build/install