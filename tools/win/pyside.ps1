. "$PSScriptRoot/util.ps1"
. "$PSScriptRoot/buildtool.ps1"
. "$PSScriptRoot/vcpkg.ps1"

function Get-PySide
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ReferencePlatform,

        [Parameter(Mandatory = $true)]
        [bool]$Reset
    )

    # Cd to the build directory
    Set-Location -Path $Path

    if ($Reset)
    {
        Write-Message -m "Cleaning pyside directory..."
        if (Test-Path -Path (Join-Path -Path $Path -ChildPath "pyside"))
        {
            Remove-Directory -Path (Join-Path -Path $Path -ChildPath "pyside")

            if ($LASTEXITCODE -ne 0)
            {
                Write-Message -t "error" "Failed to delete the pyside directory."
                exit 1
            }

            # Fail if the directory still exists
            if (Test-Path -Path (Join-Path -Path $Path -ChildPath "pyside"))
            {
                Write-Message -t "error" "Failed to delete the pyside directory."
                exit 1
            }
        }
    }

    # Check if the pyside directory exists
    if (-not (Test-Path -Path (Join-Path -Path $Path -ChildPath "pyside/.git")))
    {
        Write-Message -m "Cloning pyside repository to $Path"
        git clone "https://code.qt.io/pyside/pyside-setup" $Path/pyside

        if ($LASTEXITCODE -ne 0)
        {
            Write-Message -t "error" "Failed to clone the pyside repository."
            exit 1
        }
    }
    else
    {
        Write-Message -m "The pyside directory already exists at $( Join-Path -Path $Path -ChildPath "pyside" ). Skipping the clone."
    }

    # Get Qt version
    $Qt = Get-Version -Path $Path -ReferencePlatform $ReferencePlatform -Package "qt[0-9]*-?base"
    if ($null -eq $Qt)
    {
        Write-Message -t "error" "Failed to get the Qt version."
        exit 1
    }

    # Cd to the pyside directory
    Set-Location -Path (Join-Path -Path $Path -ChildPath "pyside")

    # List all the available branches
    $branches = git --no-pager branch --all
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to list the branches."
        exit 1
    }

    if ($null -eq $branches)
    {
        Write-Message -t "error" "No branches were found."
        exit 1
    }

    # Find the branch that matches the Qt version
    $branch = $branches | Where-Object { $_ -match ".*/($( $Qt.MAJOR_VERSION ).$( $Qt.MINOR_VERSION ).$( $Qt.PATCH_VERSION ))" }
    if ($null -eq $branch)
    {
        Write-Message -m "Warning: The branch for the Qt version $( $Qt.MAJOR_VERSION ).$( $Qt.MINOR_VERSION ).$( $Qt.PATCH_VERSION ) does not exist. Attempting to find a branch by major and minor version..."

        # If the branch does not exist, start matching by major and minor versions
        $branch = $branches | Where-Object { $_ -match ".*/($( $Qt.MAJOR_VERSION ).$( $Qt.MINOR_VERSION ).*)" } | Sort-Object -Descending | Select-Object -First 1

        if ($null -eq $branch)
        {
            Write-Message -t "error" "No branch for the major version $( $Qt.MAJOR_VERSION ) and minor version $( $Qt.MINOR_VERSION ) was found. The available branches are:`n$( $branches -join ', ' )."
            exit 1
        }
        else
        {
            Write-Message -m "No exact branch for the Qt version $( $Qt.MAJOR_VERSION ).$( $Qt.MINOR_VERSION ).$( $Qt.PATCH_VERSION ) was found. Using the latest patch version $( $branch )."
        }
    }
    if ($null -eq $matches[1])
    {
        Write-Message -t "error" "Failed to parse the branch name."
        exit 1
    }

    Write-Message -m "Checking out the branch $( $matches[1] )"
    git checkout $matches[1]

    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to checkout the branch $( $matches[1] )."
        exit 1
    }

    # We have to checkout all the submodules also but PySide2's submodule is not up-to-date so we'll have to patch
    # .gitmodules so that `url = ../pyside-tools.git` points to `url = ../pyside2-tools.git`
    if ($Qt.MAJOR_VERSION -eq "2")
    {
        $gitmodules = Join-Path -Path $Path -ChildPath "pyside/.gitmodules"
        if (-not (Test-Path -Path $gitmodules))
        {
            Write-Message -t "error" "$gitmodules does not exist."
            exit 1
        }

        Write-Message -m "Patching .gitmodules"
        $content = Get-Content -Path $gitmodules
        $content = $content -replace "pyside-tools.git", "pyside2-tools.git"
        Set-Content -Path $gitmodules -Value $content
    }

    # Update the submodules if .gitmodules exists
    if (Test-Path -Path (Join-Path -Path $Path -ChildPath "pyside/.gitmodules"))
    {
        Write-Message -m "Updating the submodules..."
        git submodule update --init --recursive
    }
}


function Get-7z
{
    $source = "https://www.7-zip.org/a/7zr.exe"
    $destination = "$env:TEMP/7zr.exe"

    Write-Message -m "Downloading 7zr.exe from $source"
    Invoke-WebRequest -Uri $source -OutFile $destination
}


function Get-LibClang
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ReferencePlatform
    )

    # Cd to the build directory
    Set-Location -Path $Path

    # Get Qt version
    $Qt = Get-Version -Path $Path -ReferencePlatform $ReferencePlatform -Package "qt[0-9]*-?base"
    if ($null -eq $Qt)
    {
        Write-Message -t "error" "Failed to get the Qt version."
        exit 1
    }


    # Determine the pyside major version (Qt5 uses PySide2 and Qt6 uses PySide6)
    if ($Qt.MAJOR_VERSION -eq "6")
    {
        $pysideMajorVersion = "6"
    }
    else
    {
        $pysideMajorVersion = "2"
    }

    $config = Join-Path -Path $PSScriptRoot -ChildPath "../config/libclang.json"

    # Load the clang configuration
    if (-not $config)
    {
        Write-Message -t "error" "$config does not exist"
        exit 1
    }
    try
    {
        $config = Get-Content -Path "$config" -Raw | ConvertFrom-Json
    }
    catch
    {
        Write-Message -t "error" "Failed to read $config file."
        exit 1
    }


    $sources = $config."pyside$pysideMajorVersion".sources
    $outFile = "$Path/libclang/libclang.7z"

    if (Test-Path -Path $outFile)
    {
        Write-Message -m "The libclang file already exists at $outFile"
    }

    # Iterate over the sources
    foreach ($source in $sources)
    {
        $url = "$source/$( $config."pyside$pysideMajorVersion".name )"

        if (-not (Test-Path $outFile))
        {
            Write-Message -m "Downloading libclang from $url"
            Invoke-WebRequest -Uri $url -OutFile $outFile
        }
        else
        {
            Write-Message -m "The libclang file already exists at $outFile"
        }

        if (-not (Test-Path -Path "$Path/libclang/bin/clang.exe"))
        {
            Get-7z
            Write-Message -m "Extracting libclang to $Path/libclang"
            & "$env:TEMP/7zr.exe" x -o"$Path" $outFile

            if ($LASTEXITCODE -ne 0)
            {
                Write-Message -t "error" "Failed to extract libclang."
                exit 1
            }
            else
            {
                Write-Message -m "Successfully extracted libclang."
                return
            }
        }
        else
        {
            return
        }
    }

    Write-Message -t "error" "Failed to download libclang."
    exit 1
}


function New-PythonDistribution
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ReferencePlatform,

        [Parameter(Mandatory = $true)]
        [bool]$Reset
    )

    $vcpkgInstallDir = Join-Path -Path $Path -ChildPath "vcpkg/vcpkg_installed"

    if ($Reset)
    {
        Write-Message -m "Cleaning python distribution..."
        if (Test-Path -Path (Join-Path -Path $Path -ChildPath "python"))
        {
            Remove-Directory -Path (Join-Path -Path $Path -ChildPath "python")

            if ($LASTEXITCODE -ne 0)
            {
                Write-Message -t "error" "Failed to delete the python directory."
                exit 1
            }

            # Fail if the directory still exists
            if (Test-Path -Path (Join-Path -Path $Path -ChildPath "python"))
            {
                Write-Message -t "error" "Failed to delete the python directory."
                exit 1
            }
        }
    }

    # Get the target python version
    $PY = Get-Version -Path $Path -ReferencePlatform $ReferencePlatform -Package "python[0-9]+"
    if ($null -eq $PY)
    {
        Write-Message -t "error" "Failed to get the Python version."
        exit 1
    }

    $fileContents = Get-VcpkgInfo -Path $Path -Package "python"

    # Iterate over each line in the file
    foreach ($line in $fileContents)
    {
        [string]$destination = ""

        # Skip lines that contain debug or test
        if ($line -match ".*/debug/.*" -or $line -match ".*\.pdb")
        {
            continue
        }

        $source = Join-Path -Path $vcpkgInstallDir -ChildPath "$line"

        # DLLs
        if ($line -match "^.*/(?:bin|DLLs)/(.*\.(?:pyd|dll))$")
        {
            $destination = Join-Path -Path $Path -ChildPath "python/DLLs/$( $matches[1] )"
        }

        # include
        if ($line -match "^.*/include/python[0-9]{1,}\.[0-9]{1,}/(.*\.h)$")
        {
            $destination = Join-Path -Path $Path -ChildPath "python/include/$( $matches[1] )"
        }

        # libs
        if ($line -match "^.*/lib/(.*\.(?:lib|pc))$")
        {
            $destination = Join-Path -Path $Path -ChildPath "python/libs/$( $matches[1] )"
        }

        # Lib
        elseif ($line -match "^.*/tools/.*/Lib/(.*\.[a-z0-9]{1,})$")
        {
            $destination = Join-Path -Path $Path -ChildPath "python/Lib/$( $matches[1] )"
        }

        # Root items
        if ($line -match "^.*/python[0-9]{1,}/([^/\\]*\.(?:exe|dll))$")
        {
            $destination = Join-Path -Path $Path -ChildPath "python/$( $matches[1] )"
        }

        # Skip if the destination is not set or the file already exist
        if ("" -eq $destination)
        {
            continue
        }
        if (Test-Path -Path $destination)
        {
            continue
        }

        Write-Message -m "Copying $source to $destination"

        $destinationDir = Split-Path -Path $destination
        if (-not (Test-Path -Path $destinationDir))
        {
            Write-Message -m "Creating directory $destinationDir"
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        Copy-Item -Path $source -Destination $destination
    }

    # Test the freshly copied python interpreter to make sure it works
    $pythonExe = Join-Path -Path $Path -ChildPath "python/python.exe"
    if (-not (Test-Path -Path $pythonExe))
    {
        Write-Message -t "error" "The python interpreter does not exist at $pythonExe."
        exit 1
    }

    Write-Message -m "Testing the python interpreter at $pythonExe"
    $output = & $pythonExe -c "print('Hello, World!')"
    if ($output -ne "Hello, World!")
    {
        Write-Message -t "error" "The python interpreter at $pythonExe failed to execute the test."
        exit 1
    }
}


function Bootstrap-PythonEnvironment
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    # Ensure pip is available by running ensurepip
    $pythonExe = Join-Path -Path $Path -ChildPath "python/python.exe"
    if (-not (Test-Path -Path $pythonExe))
    {
        Write-Message -t "error" "The python interpreter does not exist at $pythonExe."
        exit 1
    }
    Write-Message -m "Ensuring pip is available"
    $output = & $pythonExe -m ensurepip
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to ensure pip is available."
        exit 1
    }
    # Install the pip package
    Write-Message -m "Installing the pip package"
    $output = & $pythonExe -m pip install pip --upgrade
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to install the pip package."
        exit 1
    }
    # Install the PySide requirements
    Write-Message -m "Installing the PySide requirements"
    $output = & $pythonExe -m pip install -r "$Path/pyside/requirements.txt" --upgrade

    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to install the PySide requirements."
        exit 1
    }

    Write-Message -m "Updating PATH environment variable..."
    $pythonDir = Join-Path -Path $Path -ChildPath "python"
    [Environment]::SetEnvironmentVariable("PATH", "$pythonDir;$libclangDir;$env:Path", "Process")
}

function Build-PySide
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ReferencePlatform,

        [Parameter(Mandatory = $true)]
        [bool]$Reset
    )

    # Set the Qt environment variables
    $Qt = Get-Version -Path $Path -ReferencePlatform $ReferencePlatform -Package "qt[0-9]*-?base"
    if ($null -eq $Qt)
    {
        Write-Message -t "error" "Failed to get the Qt version."
        exit 1
    }

    # Determine the pyside major version (Qt5 uses PySide2 and Qt6 uses PySide6)
    if ($Qt.MAJOR_VERSION -eq "6")
    {
        $pysideMajorVersion = "6"
    }
    else
    {
        $pysideMajorVersion = "2"
    }
    Write-Message -m "Building PySide$pysideMajorVersion for Qt $( $Qt.MAJOR_VERSION ).$( $Qt.MINOR_VERSION ).$( $Qt.PATCH_VERSION )"

    # Make sure PySide2 is only built for Python 3.10 and below (PySide2 open source is only compatible with Python 3.10 and below
    $PY = Get-Version -Path $Path -ReferencePlatform $ReferencePlatform -Package "python[0-9]+"
    if ($pysideMajorVersion -eq "2" -and $PY.MAJOR_VERSION -eq "3" -and $PY.MINOR_VERSION -gt "10")
    {
        Write-Message -t "error" "PySide2 is only compatible with Python 3.10 and below. The current Python version is $( $PY.MAJOR_VERSION ).$( $PY.MINOR_VERSION )."
        exit 1
    }

    # Set the PATH environment variable
    $pythonDir = Join-Path -Path $Path -ChildPath "python"
    $llvmBinDir = Join-Path -Path $Path -ChildPath "libclang/bin"

    Write-Message -m "Setting the PATH environment variable"
    [Environment]::SetEnvironmentVariable(
            "PATH",
            "$pythonDir;$pythonDir/Scripts;$llvmBinDir;$env:Path",
            "Process"
    )

    # Configure the build
    $pysideDir = Join-Path -Path $Path -ChildPath "pyside"
    $buildDir = Join-Path -Path $pysideDir -ChildPath "build"

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

    Verify-ReferencePlatformArg -r $ReferencePlatform
    $ReferencePlatforms = Get-ReferencePlatforms

    Bootstrap-PythonEnvironment -Path $Path

    # Define the arguments in an array
    Write-Message -m "Configuring the build with Visual Studio $( $ReferencePlatforms.$ReferencePlatform.vs_version ) $( $ReferencePlatforms.$ReferencePlatform.vs_year )"
    $arguments = @(
        "--log-level=$( $global:CMakeVerbosity )",
        "-S", $pysideDir,
        "-B", $buildDir,
        "-G", "Visual Studio $( $ReferencePlatforms.$ReferencePlatform.vs_version ) $( $ReferencePlatforms.$ReferencePlatform.vs_year )",
        "-A", "x64",
        "-DLLVM_INSTALL_DIR=$Path/libclang",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_INSTALL_PREFIX=$Path/pyside/install",
        "-DBUILD_TESTS:BOOL=OFF",
        "-DSKIP_MODULES=PrintSupport;Network;Test;DBus;Xml;XmlPatterns;Help;Multimedia;MultimediaWidgets;OpenGL;OpenGLFunctions;OpenGLWidgets;Positioning;Location;Qml;Quick;QuickControls2;QuickWidgets;RemoteObjects;Scxml;Script;ScriptTools;Sensors;SerialPort;TextToSpeech;Charts;Svg;DataVisualization",
        "-DVCPKG_TARGET_TRIPLET=x64-windows",
        "-DCMAKE_TOOLCHAIN_FILE=$Path/vcpkg/scripts/buildsystems/vcpkg.cmake",
        "-DVCPKG_MANIFEST_MODE=ON",
        "-DVCPKG_MANIFEST_DIR=$Path/vcpkg"
        "-DVCPKG_INSTALLED_DIR=$Path/vcpkg/vcpkg_installed",
        "-DVCPKG_MANIFEST_INSTALL=OFF",
        "-DDISABLE_PYI=yes",
        "-DFORCE_LIMITED_API=no"
    )

    # Invoke cmake with the arguments
    & cmake.exe @arguments

    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to configure the build."
        exit 1
    }
    # Check that the build directory exists
    if (-not (Test-Path -Path $buildDir))
    {
        Write-Message -t "error" "The build directory does not exist."
        exit 1
    }

    # Build the project
    # Get the solution file from the build directory (match super project .sln file)
    $mainsolution = Get-ChildItem -Path $buildDir -Filter "*_super_project.sln"
    if ($null -eq $mainsolution)
    {
        Write-Message -t "error" "The solution file does not exist in the build directory. Was looking in $buildDir."
        exit 1
    }
    Write-Message -m "Found the main solution file: $( $mainsolution.FullName )"

    $shibokenSolution = Get-ChildItem -Path (Join-Path $buildDir -ChildPath "sources/shiboken$pysideMajorVersion") -Filter "shiboken*.sln"
    if ($null -eq $shibokenSolution)
    {
        Write-Message -t "error" "The shiboken solution file does not exist. Was looking in $( Join-Path $buildDir -ChildPath "sources/shiboken$pysideMajorVersion" )."
        exit 1
    }
    Write-Message -m "Found the shiboken solution file: $( $shibokenSolution.FullName )"
    $shibokenInstall = Join-Path $buildDir -ChildPath "sources/shiboken$pysideMajorVersion/cmake_install.cmake"
    if (-not (Test-Path -Path $shibokenInstall))
    {
        Write-Message -t "error" "The shiboken install file does not exist. Was looking for $shibokenInstall."
        exit 1
    }
    Write-Message -m "Found the shiboken install file: $shibokenInstall"

    $pysideSolution = Get-ChildItem -Path (Join-Path $buildDir -ChildPath "sources/pyside$pysideMajorVersion") -Filter "pyside*.sln"
    if ($null -eq $pysideSolution)
    {
        Write-Message -t "error" "The pyside solution file does not exist. Was looking in $( Join-Path $buildDir -ChildPath "sources/pyside$pysideMajorVersion" )."
        exit 1
    }
    Write-Message -m "Found the pyside solution file: $( $pysideSolution.FullName )"
    $pysideInstall = Join-Path $buildDir -ChildPath "sources/pyside$pysideMajorVersion/cmake_install.cmake"
    if (-not (Test-Path -Path $pysideInstall))
    {
        Write-Message -t "error" "The pyside install file does not exist. Was looking for $pysideInstall."
        exit 1
    }
    Write-Message -m "Found the pyside install file: $pysideInstall"

    # Cd to the build directory
    Set-Location -Path $buildDir

    # Build shiboken & install shiboken

    # shiboken
    Write-Message -m "Building shiboken..."
    & msbuild.exe $shibokenSolution.FullName -verbosity:$( $global:MSBuildVerbosity ) -target:Build -property:Configuration=Release -property:Platform=x64 /m /nologo
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "PySide encountered errors during the build. Continuing..."
    }
    Write-Message -m "Installing shiboken..."
    $arguments = @(
        "--log-level=$( $global:CMakeVerbosity )",
        "-P", $shibokenInstall,
        "-DCMAKE_INSTALL_LOCAL_ONLY=OFF"
    )
    & cmake.exe @arguments
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to install shiboken."
        exit 1
    }

    # pyside
    Write-Message -m "Building PySide..."
    & msbuild.exe $pysideSolution.FullName -verbosity:$( $global:MSBuildVerbosity ) -target:Build -property:Configuration=Release -property:Platform=x64 /m /nologo
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "PySide encountered errors during the build. Continuing..."
    }

    # Hacky bug fix -> in case pyi header generation fails create dummy files for each Qt module
    $qtModules = @("Core", "Gui", "Widgets", "Sql", "Concurrent")
    foreach ($module in $qtModules)
    {
        $pyiFile = Join-Path -Path $buildDir -ChildPath "sources/pyside$pysideMajorVersion/PySide$pysideMajorVersion/Qt$module/../Qt$module.pyi"
        if (-not (Test-Path -Path $pyiFile))
        {
            Write-Message -m "Creating dummy pyi file for $module"
            New-Item -Path $pyiFile -ItemType File -Force | Out-Null
        }
    }

    Write-Message -m "Installing PySide..."
    $arguments = @(
        "--log-level=$( $global:CMakeVerbosity )",
        "-P", $pysideInstall,
        "-DCMAKE_INSTALL_LOCAL_ONLY=OFF"
    )
    & cmake.exe @arguments
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to install PySide."
        exit 1
    }
}