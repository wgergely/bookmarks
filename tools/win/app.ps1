. "$PSScriptRoot/util.ps1"
. "$PSScriptRoot/buildtool.ps1"
. "$PSScriptRoot/vcpkg.ps1"


function Build-App
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ReferencePlatform,

        [Parameter(Mandatory = $true)]
        [string]$Version,

        [Parameter(Mandatory = $false)]
        [bool]$Reset
    )

    Verify-ReferencePlatformArg -r $ReferencePlatform
    $ReferencePlatforms = Get-ReferencePlatforms

    # Make build dir
    $buildDir = Join-Path -Path $Path -ChildPath "app"

    if ($Reset)
    {
        Write-Message -m "Cleaning the build directory..."
        if (Test-Path -Path $buildDir)
        {
            Remove-Directory -Path $buildDir

            if ($LASTEXITCODE -ne 0)
            {
                Write-Message -t "error" "Failed to delete the build directory."
                exit 1
            }

            # Fail if the directory still exists
            if (Test-Path -Path $buildDir)
            {
                Write-Message -t "error" "Failed to delete the build directory."
                exit 1
            }
        }
    }

    [version]$sourceVersion = Get-SourceVersion
    if ($null -eq $sourceVersion)
    {
        Write-Message -t "error" -m "Failed to get the source version."
        exit 1
    }
    if ("" -eq $sourceVersion.ToString())
    {
        Write-Message -t "error" -m "The source version is empty."
        exit 1
    }

    # Verify source dir
    $sourceDir = Join-Path -Path $PSScriptRoot -ChildPath "../../src"
    if (-not (Test-Path -Path $sourceDir))
    {
        Write-Message -t "error" -m "Source directory not found: $sourceDir"
    }

    Write-Message -m "Configuring the build with Visual Studio $( $ReferencePlatforms.$ReferencePlatform.vs_version ) $( $ReferencePlatforms.$ReferencePlatform.vs_year )"
    $arguments = @(
        "--log-level=$( $global:CMakeVerbosity )"
        "-S", $sourceDir,
        "-B", $buildDir,
        "-G", "Visual Studio $( $ReferencePlatforms.$ReferencePlatform.vs_version ) $( $ReferencePlatforms.$ReferencePlatform.vs_year )",
        "-A", "x64",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_INSTALL_PREFIX=$Path/app/install",
        "-DVCPKG_DIR=$Path/vcpkg",
        "-DVCPKG_TARGET_TRIPLET=x64-windows",
        "-DCMAKE_TOOLCHAIN_FILE=$Path/vcpkg/scripts/buildsystems/vcpkg.cmake",
        "-DVCPKG_MANIFEST_MODE=ON",
        "-DVCPKG_MANIFEST_DIR=$Path/vcpkg"
        "-DVCPKG_INSTALLED_DIR=$Path/vcpkg/vcpkg_installed",
        "-DVCPKG_MANIFEST_INSTALL=OFF",
        "-DBUILD_APP=ON",
        "-DBUILD_IMAGEUTIL=ON",
        "-DBUILD_PY=ON",
        "-DBookmarks_VERSION=$($sourceVersion.ToString() )"
    )

    # Invoke cmake with the arguments
    & cmake.exe $arguments

    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" -m "Failed to configure the build."
        exit 1
    }

    # Build the project
    $mainsolution = Get-ChildItem -Path $buildDir -Filter "*Bookmarks.sln"
    if ($null -eq $mainsolution)
    {
        Write-Message -t "error" "The solution file does not exist in the build directory. Was looking in $buildDir."
        exit 1
    }
    Write-Message -m "Found the main solution file: $( $mainsolution.FullName )"

    Set-Location -Path $buildDir

    Write-Message -m "Building the app..."
    & msbuild.exe $mainsolution.FullName -verbosity:$( $global:MSBuildVerbosity ) /t:Build /p:Configuration=Release /p:Platform=x64 /m /nologo

    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" -m "Failed to build the app."
        exit 1
    }

    $cmake_install = Join-Path $buildDir -ChildPath "cmake_install.cmake"
    if (-not (Test-Path -Path $cmake_install))
    {
        Write-Message -t "error" "The shiboken install file does not exist. Was looking for $cmake_install."
        exit 1
    }

    Write-Message -m "Installing app..."
    $arguments = @(
        "--log-level=$( $global:CMakeVerbosity )",
        "-P", $cmake_install,
        "-DCMAKE_INSTALL_LOCAL_ONLY=OFF"
    )
    & cmake @arguments
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to install shiboken."
        exit 1
    }
}