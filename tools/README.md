# Build Tools

This folder contains the build tools used to generate dependencies and environment for the Bookmarks application.
We build against the [VFX Reference Platform](https://vfxplatform.com/) specifications and use [vcpkg](https://github.com/microsoft/vcpkg) to manage dependencies.

> **_NOTE:_** Only Windows build scripts are provided.

### Build Instructions

Run `win-build.ps1` with the desired Reference Platform version (e.g. CY2024 or CY2023):

```powershell
./win-build.ps1 -ReferencePlatform CY2024
```

### Prerequisites

- CMake 3.18 or later
- Git 2.28 or later
- PowerShell 5.0 or later

### Build Steps

`win-build.ps1` runs the following build steps:
- `[setup]`: Downloads and installs a reference platform compatible `Visual Studio Build Tools` version
- `[vcpkg]`: Builds binary dependencies using vcpkg and predefined manifest files
- `[pyside]`: Builds PySide from source
- `[app]`: Builds application libraries and executables
- `[dist]`: Creates the application distribution folder
- `[installer]`: Creates the application installer

Steps can be skipped or reset using `-Skip*` and `-Reset*` flags:

```powershell
./win-build.ps1 -r CY2024 -SkipVcpkg -SkipPySide -SkipApp -SkipDist -ResetInstaller
```

### Application Package

The script will, by default, place all build artifacts to `C:/build/{ReferencePlatform}-{Version}/dist`.
The `dist/python.exe` can be used as a python interpreter for the application in IDEs like PyCharm. 
