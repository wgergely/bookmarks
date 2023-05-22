# Bookmarks: Visual Studio Build Process

This repository contains the build script setup for the Bookmarks on Windows. The build process is designed to be used with Visual Studio 2019 and above, and requires the use of the Visual Studio x64 command console - preferably from an elevated command prompt. Prior to building, ensure that cmake, git, and Visual Studio are installed on the system.

## Build Process Summary

The top-level `build.bat` script is responsible for building the application package. It follows these stages:

1. The CMake wrapper sets up the build, downloads dependencies, and builds the following libraries using vcpkg:
   - OpenImageIO
   - Qt
   - FFMpeg
2. PySide and all other dependencies are built against the vcpkg libraries.
3. Finally, all the build artifacts are gathered and copied to the `./package/build/package` folder.

## Usage

1. Open the Visual Studio x64 command console.
2. Navigate to the project directory.
3. Run the `build.bat` script.

## Build Files

### build.bat

This is the top-level build script responsible for orchestrating the build process. It invokes cmake to configure Bookmarks.sln and calls the secondary build scripts in the following order:

* ##### Bookmarks.sln
    It sets up the project and specifies various options and dependencies. Make sure you have the required tools and dependencies installed before running CMake. The vcpkg library dependencies built by the CMake script include:
    - OpenImageIO
    - Qt
    - FFMpeg
* ##### build-imageutil.bat
    This script builds the imageutil project (the library used by bookmarks to wrap OpenImageIO).
* ##### build-pyside.bat
    This script builds PySide from source. It performs the following tasks:
    - Copies Python files and libraries from the vcpkg directory to the Python directory.
    - Clones the PySide repository and checks out the required version.
    - Installs necessary Python dependencies.
    - Sets up the build environment.
    - Configures CMake with appropriate options.
    - Builds the PySide solution.
* ##### build-package.bat
    Responsible for packaging the Bookmarks application for distribution. It performs the following tasks:
    - Creates the necessary directories for the package.
    - Copies the required files, including DLLs, plugins, and dependencies, to the package directory.
    - Installs Python dependencies.
    - Copies the Bookmarks source code to the package.