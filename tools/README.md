# Bookmarks: Windows Package

This folder contains the build scripts of Bookmarks' Windows distribution. Please note other platforms are not (yet) supported.

The build process is designed to be used with Visual Studio 2019 and above, and requires the use of the Visual Studio x64 command console - preferably from an elevated command prompt. Prior to building, ensure that cmake, git, and Visual Studio are installed on the build system.


## Build Process Summary

The top-level `build.bat` script is responsible for building the application package including all binary dependencies.
Build.bat uses CMake to build and acquire dependencies (Qt, FFMpeg and OpenImageIO and PySide).

All final build artifacts are gathered and copied to the `./package/build/package`.


## Usage

From Visual Studio x64 command console navigate to the project directory andrun the `build.bat`.

```

cd C:/bookmarks/package
cmd /c build.bat

```

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
* ##### Build-Dist.bat
    Responsible for packaging the Bookmarks application for distribution. It performs the following tasks:
    - Creates the necessary directories for the package.
    - Copies the required files, including DLLs, plugins, and dependencies, to the package directory.
    - Installs Python dependencies.
    - Copies the Bookmarks source code to the package.