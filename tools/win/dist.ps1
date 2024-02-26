. "$PSScriptRoot/util.ps1"
. "$PSScriptRoot/buildtool.ps1"
. "$PSScriptRoot/vcpkg.ps1"


function Get-Constants {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $h = Join-Path -Path $PSScriptRoot -ChildPath "../../src/include/dist.h"
    if (-not (Test-Path -Path $h)) {
        Write-Message -t "error" "$h does not exist."
        exit 1
    }

    $content = Get-Content -Path $h
    if ($null -eq $content) {
        Write-Message -t "error" "No content found in $h."
        exit 1
    }

    $constants = @{
        "bin_dir"              = ""
        "core_modules_dir"     = ""
        "internal_modules_dir" = ""
        "shared_modules_dir"   = ""
    }
    foreach ($line in $content) {
        if ($line -match "^.*BIN_DIR\s*=\s*[`"']([a-z]+)[`"'];$") {
            $constants["bin_dir"] = $matches[1]
        }
        if ($line -match "^.*CORE_MODULES_DIR\s*=\s*[`"']([a-z]+)[`"'];$") {
            $constants["core_modules_dir"] = $matches[1]
        }
        if ($line -match "^.*INTERNAL_MODULES_DIR\s*=\s*[`"']([a-z]+)[`"'];$") {
            $constants["internal_modules_dir"] = $matches[1]
        }
        if ($line -match "^.*SHARED_MODULES_DIR\s*=\s*[`"']([a-z]+)[`"'];$") {
            $constants["shared_modules_dir"] = $matches[1]
        }
    }

    # Verify that all constants have been set
    foreach ($key in $constants.Keys) {
        if ($constants[$key] -eq "") {
            Write-Message -t "error" "Failed to parse $h. $key is not set."
            exit 1
        }
    }
    return $constants
}


function Get-Dependencies {
    param(
        [string]$Path
    )

    # Ensure dumpbin is available
    if (-not (Get-Command "dumpbin" -ErrorAction SilentlyContinue)) {
        Write-Message -t "error" "dumpbin is not available. Ensure Visual Studio Build Tools are installed and accessible."
        exit 1
    }

    if (-not (Test-Path -Path $Path)) {
        Write-Message -t "error" "The path $Path does not exist."
        exit 1
    }

    $dumpbinOutput = & dumpbin /DEPENDENTS $Path | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Message -t "error" "Failed to run dumpbin:`n$dumpbinOutput"
        exit 1
    }

    if ($null -eq $dumpbinOutput) {
        Write-Message -t "error" "No output from dumpbin."
        exit 1
    }

    $dependencies = $dumpbinOutput -split "`r`n" | Where-Object { $_ -match "^.*\.dll$" } | ForEach-Object { $_.Trim() }
    
    if ($null -eq $dependencies) {
        Write-Message -t "error" "No dependencies found."
        exit 1
    }

    return $dependencies | Sort-Object -Unique
}


function Compare-Files {
    param(
        [Parameter(Mandatory = $true)]
        [Alias("s")]
        [string]$Source,

        [Parameter(Mandatory = $true)]
        [Alias("d")]
        [string]$Destination
    )

    if (-not (Test-Path -Path $destination)) {
        return $true
    }

    $sourceSize = (Get-Item -Path $source).length
    $destinationSize = (Get-Item -Path $destination).length
    if ($sourceSize -ne $destinationSize) {
        return $true
    }
    Write-Message -t "warning" -m "Skipping $destination, already exists..."
    return $false
}


function Build-Dist {
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
    
    $constants = Get-Constants -Path $Path
    
    # Set up directory structure
    $buildDir = Join-Path -Path $Path -ChildPath "dist/$($Version.ToString())"
    New-Directory -Path $buildDir

    if ($Reset) {
        Write-Message -m "Resetting the dist directory..."
        Remove-Item -Path $buildDir -Recurse -Force
        New-Directory -Path $buildDir
    }

    # Create all the directories
    # loop through the values of constants and create the directories
    foreach ($key in $constants.Keys) {
        $dir = Join-Path -Path $buildDir -ChildPath $constants[$key]
        New-Directory -Path $dir
    }

    $vcpkgInstallDir = Join-Path -Path $Path -ChildPath "vcpkg/vcpkg_installed"
    if (-not (Test-Path -Path $vcpkgInstallDir)) {
        Write-Message -t "error" "The vcpkg_installed folder does not exist."
        exit 1
    }

    $fileContents = Get-VcpkgInfo -Path $Path -Package "qt*base"
    $skipModules = @("DBus", "Network", "OpenGL", "Test", "Sql", "Xml", "PrintSupport")

    # Qt    
    foreach ($line in $fileContents) {
        [string]$destination = ""

        # Skip lines that contain debug or test
        if ($line -match ".*[\\/]debug[\\/].*" -or -not ($line -match ".*\.dll")) {
            continue
        }
        
        $source = Join-Path -Path $vcpkgInstallDir -ChildPath "$line"

        # Skip modules
        $skip = $false
        foreach ($module in $skipModules) {
            if ($line -match ".*$module.*") {
                $skip = $true
            }
        }

        if ($skip) {
            continue
        }

        # DLLs
        if ($line -match "^.*[\\/]tools[\\/].*[\\/]bin[\\/](.*\.dll)$") {
            $destination = Join-Path -Path $buildDir -ChildPath "bin/$($matches[1])"
        }

        # Plugins
        if ($line -match "^.*[\\/]plugins[\\/](.*\.dll)$") {
            $destination = Join-Path -Path $buildDir -ChildPath "bin/$($matches[1])"
        }


        # Skip if the destination is not set or the file already exist
        if ("" -eq $destination) {
            continue
        }

        Write-Message -m "Found $line"

        $destinationDir = Split-Path -Path $destination
        if (-not (Test-Path -Path $destinationDir)) {
            Write-Message -m "Creating directory $destinationDir"
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        
        if (-not (Compare-Files -s $source -d $destination)) {
            continue
        }

        Write-Message -m "Copying $source to $destination"
        Copy-Item -Path $source -Destination $destination
    }

    # Get Qt's c++ runtime dependencies using dumbin from the QtCore.dll (we have to match the line from $fileContents)
    $line = $fileContents | Where-Object { $_ -match "^(.*/tools/.*/Qt.*Core\.dll)$" }
    $dll = Join-Path -Path $vcpkgInstallDir -ChildPath $matches[1]
    if (-not (Test-Path -Path $dll)) {
        Write-Message -t "error" "QtCore.dll not found."
        exit 1
    }

    $qtCoreDependencies = Get-Dependencies -Path $dll
    # Match msvcp*.dll and vcruntime*.dll
    $msvcRuntimes = $qtCoreDependencies | Where-Object { $_ -match ".*msvcp.*\.dll" -or $_ -match ".*vcruntime.*\.dll" }
    
    # Copy the runtime dependencies to the dist root
    foreach ($runtime in $msvcRuntimes) {
        # Get the windows system32 directory
        $system32 = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::System)
        $source = Join-Path -Path $system32 -ChildPath "$runtime"
        $destination = Join-Path -Path $buildDir -ChildPath "bin/$runtime"

        if (-not (Test-Path -Path $source)) {
            Write-Message -t "error" "$runtime not found in $system32."
            exit 1
        }

        Write-Message -m "Found $runtime"

        if (-not (Compare-Files -s $source -d $destination)) {
            continue
        }

        Write-Message -m "Copying $source to $destination"
        Copy-Item -Path $source -Destination $destination
    }

    # FFmpeg
    $fileContents = Get-VcpkgInfo -Path $Path -Package "ffmpeg"

    foreach ($line in $fileContents) {
        [string]$destination = ""

        # Skip lines that contain debug
        if (($line -match ".*[\\/]debug[\\/].*") -or ($line -match ".*\.pdb")) {
            continue
        }
        
        $source = Join-Path -Path $vcpkgInstallDir -ChildPath "$line"

        # DLLs
        if ($line -match "^.*[\\/]tools[\\/].*[\\/](.*\.(?:dll|exe))$") {
            $destination = Join-Path -Path $buildDir -ChildPath "bin/$($matches[1])"
        }

        # Skip if the destination is not set or the file already exist
        if ("" -eq $destination) {
            continue
        }

        Write-Message -m "Found $line"
        
        $destinationDir = Split-Path -Path $destination
        if (-not (Test-Path -Path $destinationDir)) {
            Write-Message -m "Creating directory $destinationDir"
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        
        if (-not (Compare-Files -s $source -d $destination)) {
            continue
        }
        
        Write-Message -m "Copying $source to $destination"
        Copy-Item -Path $source -Destination $destination
    }

    # OpenImageIO
    $fileContents = Get-VcpkgInfo -Path $Path -Package "openimageio"

    foreach ($line in $fileContents) {
        [string]$destination = ""

        # Skip lines that contain debug
        if (($line -match ".*[\\/]debug[\\/].*") -or ($line -match ".*\.pdb")) {
            continue
        }
        
        $source = Join-Path -Path $vcpkgInstallDir -ChildPath "$line"

        # DLLs
        if ($line -match "^.*[\\/]tools[\\/].*[\\/](.*\.(?:dll|exe))$") {
            $destination = Join-Path -Path $buildDir -ChildPath "bin/$($matches[1])"
        }

        # Pyd
        if ($line -match "^.*[\\/]site-packages[\\/].*[\\/](.*\.(?:pyd))$") {
            $destination = Join-Path -Path $buildDir -ChildPath "shared/$($matches[1])"
        }

        # Skip if the destination is not set or the file already exist
        if ("" -eq $destination) {
            continue
        }

        Write-Message -m "Found $line"

        $destinationDir = Split-Path -Path $destination
        if (-not (Test-Path -Path $destinationDir)) {
            Write-Message -m "Creating directory $destinationDir"
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        
        if (-not (Compare-Files -s $source -d $destination)) {
            continue
        }
        
        Write-Message -m "Copying $source to $destination"
        Copy-Item -Path $source -Destination $destination
    }

    # Python
    $fileContents = Get-VcpkgInfo -Path $Path -Package "python.*"

    # We don't want to ship the app with all the python libraries, so we'll zip them up into a python$VERSION_MAJOR.$VERSION_MINOR.zip
    $PY = Get-Version -Path $Path -ReferencePlatform $ReferencePlatform -Package "python*"
    $pythonZip = Join-Path -Path $buildDir -ChildPath "bin/python$($PY.MAJOR_VERSION)$($PY.MINOR_VERSION).zip"
    $pythonZipExists = Test-Path -Path $pythonZip

    $tempPythonLibs = Join-Path -Path $buildDir -ChildPath "__temp__"

    foreach ($line in $fileContents) {
        [string]$destination = ""

        # Skip lines that contain debug
        if (($line -match ".*[\\/]debug[\\/].*") -or ($line -match ".*\.pdb")) {
            continue
        }
        
        $source = Join-Path -Path $vcpkgInstallDir -ChildPath "$line"

        # PYDs
        if ($line -match "^.*[\\/]tools[\\/].*[\\/]DLLs[\\/](.*\.pyd)$") {
            $destination = Join-Path -Path $buildDir -ChildPath "internal/$($matches[1])"
        }

        # DLLs
        if ($line -match "^.*[\\/]tools[\\/].*[\\/]DLLs[\\/](.*\.dll)$") {
            $destination = Join-Path -Path $buildDir -ChildPath "bin/$($matches[1])"
        }

        # Lib
        if (-not $pythonZipExists -and $line -match "^.*[\\/]tools[\\/].*[\\/]Lib[\\/](.*\..{1,})$") {
            $destination = Join-Path -Path $tempPythonLibs -ChildPath "$($matches[1])"
        }
        
        # Python dlls
        if ($line -match "^.*[\\/](python(?:[0-9]*|w)\.(?:dll))$") {
            $destination = Join-Path -Path $buildDir -ChildPath "bin/$($matches[1])"
        }
        
        # Skip if the destination is not set or the file already exist
        if ("" -eq $destination) {
            continue
        }

        Write-Message -m "Found $line"

        $destinationDir = Split-Path -Path $destination
        if (-not (Test-Path -Path $destinationDir)) {
            Write-Message -m "Creating directory $destinationDir"
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        
        if (-not (Compare-Files -s $source -d $destination)) {
            continue
        }
        
        Write-Message -m "Copying $source to $destination"
        Copy-Item -Path $source -Destination $destination
    }

    # Check if the python zip already exists
    if ($pythonZipExists) {
        Write-Message -t "warning" "$pythonZip already exists. .Skipping"
    }
    else {

        if (-not (Test-Path -Path $tempPythonLibs)) {
            Write-Message -t "error" "$tempPythonLibs does not exist."
            exit 1
        }
     
        Write-Message -m "Compressing $tempPythonLibs into $pythonZip"   
        Compress-Archive -Path "$tempPythonLibs/*" -DestinationPath $pythonZip -Force
        Remove-Item -Path $tempPythonLibs -Recurse -Force
    }

    # Pyside
    $pysideInstallDir = Join-Path -Path $Path -ChildPath "pyside/install"
    if (-not (Test-Path -Path $pysideInstallDir)) {
        Write-Message -t "error" "$pysideInstallDir does not exist."
        exit 1
    }
    
    # Iterate through all files recurisvely
    $files = Get-ChildItem -Path $pysideInstallDir -Recurse
    if ($null -eq $files) {
        Write-Message -t "error" "No files found in $pysideInstallDir."
        exit 1
    }


    foreach ($file in $files) {
        [string]$destination = ""

        $source = $file.FullName

        # Skip directories
        if ($file.PSIsContainer) {
            continue
        }

        if ($source -match "^.*[\\/]bin[\\/](.*\.(?:dll|exe))$") {
            $destination = Join-Path -Path $buildDir -ChildPath "bin/$($matches[1])"
        }

        if ($source -match "^.*[\\/]site-packages[\\/](.*\.(?:py|pyd|))$") {
            $destination = Join-Path -Path $buildDir -ChildPath "internal/$($matches[1])"
        }
        
        if ("" -eq $destination) {
            Write-Host "Skipping $source"
            continue
        }

        Write-Message -m "Found $(Split-Path -Path $source -Leaf)"

        $destinationDir = Split-Path -Path $destination
        if (-not (Test-Path -Path $destinationDir)) {
            Write-Message -m "Creating directory $destinationDir"
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }

        if (-not (Compare-Files -s $source -d $destination)) {
            continue
        }

        Write-Message -m "Copying $source to $destination"
        Copy-Item -Path $source -Destination $destination
    }

    # app
    $appInstallDir = Join-Path -Path $Path -ChildPath "app/install"
    if (-not (Test-Path -Path $appInstallDir)) {
        Write-Message -t "error" "$appInstallDir does not exist."
        exit 1
    }

    # Iterate through all files recurisvely
    $files = Get-ChildItem -Path $appInstallDir -Recurse
    if ($null -eq $files) {
        Write-Message -t "error" "No files found in $appInstallDir."
        exit 1
    }

    foreach ($file in $files) {
        [string]$destination = ""

        $source = $file.FullName

        # Skip directories
        if ($file.PSIsContainer) {
            continue
        }
        
        if ($source -match "^.*[\\/]bin[\\/]((?:Bookmarks.*)\.exe)$") {
            $destination = Join-Path -Path $buildDir -ChildPath "$($matches[1])"
        }
        if ($source -match "^.*[\\/]bin[\\/]((?!(?:Bookmarks.*)\.exe).*)$") {
            $destination = Join-Path -Path $buildDir -ChildPath "bin/$($matches[1])"
        }
        if ($source -match "^.*[\\/]lib[\\/]site-packages[\\/](.*\.pyd)$") {
            $destination = Join-Path -Path $buildDir -ChildPath "shared/$($matches[1])"
        }
        
        if ("" -eq $destination) {
            Write-Host "Skipping $source"
            continue
        }

        Write-Message -m "Found $(Split-Path -Path $source -Leaf)"

        $destinationDir = Split-Path -Path $destination
        if (-not (Test-Path -Path $destinationDir)) {
            Write-Message -m "Creating directory $destinationDir"
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }

        Write-Message -m "Copying $source to $destination"
        Copy-Item -Path $source -Destination $destination
    }


    # Main Python package
    $mainPythonPackage = Join-Path -Path $PSScriptRoot -ChildPath "../../bookmarks"

    if (-not (Test-Path -Path $mainPythonPackage)) {
        Write-Message -t "error" "$mainPythonPackage does not exist."
        exit 1
    }

    $destination = Join-Path -Path $buildDir -ChildPath "core"
    $destinationDir = Join-Path -Path $destination -ChildPath "bookmarks"

    # We'll always override the main python package
    # Remove folder if it exists
    if (Test-Path -Path $destinationDir) {
        Remove-Item -Path $destinationDir -Recurse -Force
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Message -t "error" "Failed to remove $destinationDir."
        exit 1
    }

    if (-not (Test-Path -Path $destinationDir)) {
        Write-Message -m "Creating directory $destinationDir"
        New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
    }

    Write-Message -m "Copying $mainPythonPackage to $destination"
    Copy-Item -Path $mainPythonPackage -Destination $destination -Recurse -Force
    if ($LASTEXITCODE -ne 0) {
        Write-Message -t "error" "Failed to copy $mainPythonPackage to $destination."
        exit 1
    }

    # Install main python package dependencies
    $pythonExe = Join-Path -Path $Path -ChildPath "python/python.exe"
    if (-not (Test-Path -Path $pythonExe)) {
        Write-Message -t "error" "$pythonExe does not exist."
        exit 1
    }

    $requirementsFile = Join-Path -Path $PSScriptRoot -ChildPath "../../requirements.txt"
    if (-not (Test-Path -Path $requirementsFile)) {
        Write-Message -t "error" "$requirementsFile does not exist."
        exit 1
    }

    # install target is the shared folder
    $installTarget = Join-Path -Path $buildDir -ChildPath "shared"
    if (-not (Test-Path -Path $installTarget)) {
        Write-Message -t "error" "$installTarget does not exist."
        exit 1
    }

    Write-Message -m "Installing main python package dependencies..."
    & $pythonExe -m pip install -r $requirementsFile --target $installTarget
    if ($LASTEXITCODE -ne 0) {
        Write-Message -t "error" "Failed to install main python package dependencies."
        exit 1
    }
}