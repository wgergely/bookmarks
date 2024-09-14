# Build Tools

This folder contains the build tools used to build the Bookmarks app and its dependencies.
The build system uses the [VFX Reference Platform](https://vfxplatform.com/) specifications
and [vcpkg](https://github.com/microsoft/vcpkg) to manage binary dependencies.

The build script is fully managed and in principle, should install appropriate build tools based on `config/.*.json` files.

> **_NOTE:_** Only **Windows** build is supported at the moment.

> **_NOTE:_** The non-commercial PySide2 only supports Python 3.10 and below. Houdini 20.5 ships with Python 3.11 and 
> PySide2. If required, PySide2 can be copied over manually (make sure to copy all extra dll
> dependencies and PySide modules) from the Houdini app folder.


### Build Instructions

On Windows, call `win-build.ps1` from a PowerShell command prompt with the desired Reference Platform version (for 
example, CY2024), and arguments:

```powershell
# Build the app using the CY2024 reference platform
./win-build.ps1 -ReferencePlatform CY2024

# The build stemp can be skipped or reset using the following flags
./win-build.ps1 `
    -BuildDir D:\build `
    -ReferencePlatform CY2023 `
    -[Skip|Reset]Vcpkg `
    -[Skip|Reset]PySide `
    -[Skip|Reset]App `
    -[Skip|Reset]Dist `
    -[Skip|Reset]Installer
```

`win-build.ps1` runs the following build steps:
- `[setup]`: Downloads and installs a reference platform compatible `Visual Studio Build Tools` version
- `[vcpkg]`: Builds binary dependencies using vcpkg and predefined manifest files
- `[pyside]`: Builds PySide from source
- `[app]`: Builds app libraries and executables
- `[dist]`: Creates the app distribution folder
- `[installer]`: Creates the app installer

### Prerequisites

- Internet connection
- CMake 3.18 or later
- Git 2.28 or later
- PowerShell 5.0 or later

The build script makes a reasonable effort to install the required tools and dependencies.
By default, places build artifacts are saved to `C:/build/{ReferencePlatform}-{Version}/dist/{Version}`.

`dist/bin/python.exe` is the integrated Python interpreter and `dist/bin/python-with-core.exe` the interpreter
with the core python module also loaded.




