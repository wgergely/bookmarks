# Build Tools

This folder contains the build tools used to build the Bookmarks app and its dependencies.
The build system uses the [VFX Reference Platform](https://vfxplatform.com/) specifications
and [vcpkg](https://github.com/microsoft/vcpkg) to manage binary dependencies.

The build script is fully managed and in principle, should install appropriate build tools based on `config/.*.json` files.

> **_NOTE:_** Only Windows build scripts are provided.

> **_NOTE:_** The non-commercial PySide2 only supports Python 3.10 and below. Houdini 20.5 ships with Python 3.11 and PySide2, if required, that custom PySide2 is available from the app distribution.


### Build Instructions

On Windows, call `win-build.ps1` with the desired Reference Platform version, for example, CY2024 or CY2023, and arguments:

```powershell
./win-build.ps1 -ReferencePlatform CY2024
```

```powershell
./win-build.ps1 `
    -BuildDir D:\build `
    -ReferencePlatform CY2023 `
    -[Skip|Reset]Vcpkg `
    -[Skip|Reset]PySide `
    -[Skip|Reset]App `
    -[Skip|Reset]Dist `
    -[Skip|Reset]Installer

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
- `[app]`: Builds app libraries and executables
- `[dist]`: Creates the app distribution folder
- `[installer]`: Creates the app installer

Steps can be skipped or reset using `-Skip*` and `-Reset*` flags:

```powershell
./win-build.ps1 -r CY2024 -SkipVcpkg -SkipPySide -SkipApp -SkipDist -ResetInstaller
```

### Application Package

The script, by default, places build artifacts to `C:/build/{ReferencePlatform}-{Version}/dist/{Version}`.
The `dist/bin/python.exe` is the integrated Python interpreter and `dist/bin/python-with-core.exe` the interpreter
with the core python module also loaded.

### Notes




