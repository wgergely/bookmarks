# Get the python package's version number from the __init__.py file
# The file located at ../bookmarks/__init__.py


param (
    [Parameter(HelpMessage="Enter the VFX Reference Platform name (e.g. CY2022) to build against.")]
    [Alias("r")]
    [ValidateSet("CY2021", "CY2022", "CY2023", "CY2024")]
    [string]$ReferencePlatform="CY2022",
    
    [Parameter(HelpMessage="Enter the path to the build prefix directory (e.g. C:\build). This is where the subsequent build files will be generated.")]
    [Alias("p")]
    [string]$Prefix=""
)


function Get-BookmarksVersion {
    $PathToInitPy = Join-Path -Path $PSScriptRoot -ChildPath "../bookmarks/__init__.py"
    
    # Ensure __init__.py exists
    if (!(Test-Path -Path $PathToInitPy)) {
        Write-Error "Unable to locate the __init__.py file at path: $PathToInitPy"
        return $null
    }
    # Read __init__.py's contents
    $fileContents = Get-Content -Path $PathToInitPy
    
    # Search for the __version__ variable
    $versionLine = $fileContents | Where-Object { $_ -match "^__version__\s*=\s*['`"](.+?)['`"]$" }
    if ($versionLine -eq $null) {
        Write-Error "Version information not found in __init__.py."
        return $null
    }

    # Cast to [version] type
    try {
        [version]$version = $Matches[1]
        Write-Host "[build-win.ps1] Bookmarks package version: $($version.ToString())"
        return $version
    }
    catch {
        Write-Error "Version found but failed to cast string to [version] type."s
        return $null
    }
}


function Find-VisualStudio {
    $vsVersionMap = @{
        "CY2024" = @{ "Min" = [version]"17.4"; "Max" = [version]"18.0" }
        "CY2023" = @{ "Min" = [version]"17.0"; "Max" = [version]"17.4" }
        "CY2022" = @{ "Min" = [version]"16.9"; "Max" = [version]"17.0" }
        "CY2021" = @{ "Min" = [version]"15.0"; "Max" = [version]"16.0" }
    }

    $vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vsWhere)) {
        Write-Error "[build-win.ps1] Error: `vswhere.exe` not found. Please ensure the Visual Studio build tools are installed."
        return ""
    }

    if (-not $vsVersionMap.ContainsKey($ReferencePlatform)) {
        Write-Error "[build-win.ps1] Error: Reference platform $ReferencePlatform is not recognised. Please consult https://vfxplatform.com for more information."
        return ""
    }

    $requiredVsVersionRange = $vsVersionMap[$ReferencePlatform]
    $vsInstances = & $vsWhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json

    $compatibleVSInstance = $null
    foreach ($instance in $vsInstances) {
        $instanceVersion = New-Object Version $instance.installationVersion
        if ($instanceVersion -ge $requiredVsVersionRange["Min"] -and $instanceVersion -lt $requiredVsVersionRange["Max"]) {
            $compatibleVSInstance = $instance
            break
        }
    }

    if ($null -eq $compatibleVSInstance) {
        [string] $minVersion = $requiredVsVersionRange["Min"].ToString()
        [string] $maxVersion = $requiredVsVersionRange["Max"].ToString()
        Write-Error "[build-win.ps1] Error: Couldn't find a compatible Visual Studio version for reference platform $ReferencePlatform (was expecting >=$minVersion & <$maxVersion). Please ensure the Visual Studio build tools are installed."
        return ""
    } else {
        Write-Host "[build-win.ps1] Reference Platform $ReferencePlatform`: Found Visual Studio $($compatibleVSInstance.installationVersion)"
    }

    $vsPath = $compatibleVSInstance.installationPath
    $vcVars64 = "$vsPath\VC\Auxiliary\Build\vcvars64.bat"
    if (-not (Test-Path $vcVars64)) {
        Write-Error "[build-win.ps1] Error: `vcvars64.bat` not found in detected Visual Studio path."
        return ""
    } else {
        Write-Host "[build-win.ps1] Found $vcVars64"
    }

    # Return the path to vcvars64.bat
    return $vcVars64
}


function Create-Directory {
    param (
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        Write-Host "[build-win.ps1] Creating directory $Path"
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}


function Delete-Directory {
    param (
        [string]$Path
    )

    if (Test-Path $Path) {
        Write-Host "[build-win.ps1] Deleting directory $Path"
        Remove-Item -Recurse -Force $Path
    }
}


function Clone-VcpkgRepository {
    param(
        [string]$DestinationFolder
    )

    # Make sure the destination folder exists
    if (-not (Test-Path -Path $DestinationFolder)) {
        Write-Error "[build-win.ps1] Error: The destination folder does not exist at path: $DestinationFolder"
        exit 1
    }

    $RepoZipUrl = "https://github.com/microsoft/vcpkg/archive/refs/heads/master.zip"
    $TempZipFolder = Join-Path -Path $DestinationFolder -ChildPath "temp_vcpkg"
    $ZipFile = Join-Path -Path $TempZipFolder -ChildPath "vcpkg-master.zip"

    # Create temporary folder for ZIP file
    New-Item -ItemType Directory -Path $TempZipFolder -Force | Out-Null

    # Download the repository ZIP file
    Write-Host "Downloading vcpkg repository..."
    Invoke-WebRequest -Uri $RepoZipUrl -OutFile $ZipFile

    # Extract the ZIP file to temporary folder
    Write-Host "Extracting vcpkg repository..."
    Expand-Archive -Path $ZipFile -DestinationPath $TempZipFolder -Force

    # Move contents from vcpkg-master to the destination
    $ExtractedFolder = Join-Path -Path $TempZipFolder -ChildPath "vcpkg-master"
    Get-ChildItem -Path $ExtractedFolder | Move-Item -Destination $DestinationFolder -Force

    # Clean up: Remove the ZIP file and temporary folder
    Remove-Item -Path $ZipFile -Force
    Remove-Item -Path $TempZipFolder -Recurse -Force

    Write-Host "vcpkg repository cloned successfully to $DestinationFolder"
}



$MainFunction = {
    [string] $vcVars64 = Find-VisualStudio
    if ($vcVars64 -eq "") {
        exit 1
    }
    
    # Set up the environment for building with Visual Studio
    Write-Host "[build-win.ps1] Setting up the environment for building with Visual Studio..."
    & $vcVars64

    # Get the version number from the __init__.py file
    $packageVersion = Get-BookmarksVersion
    if ($packageVersion -eq $null) {
        exit 1
    }

    # Set the build directory
    if ($Prefix -eq "") {
        [string]$BuildDir = Join-Path -Path $PSScriptRoot -ChildPath "../build/win64/$ReferencePlatform/$($packageVersion.ToString())"
    } else {
        [string]$BuildDir = $Prefix.TrimEnd("\").TrimEnd("/")
        # Make sure the prefix exists
        if (-not (Test-Path -Path $Prefix)) {
            Write-Error "[build-win.ps1] Error: The build prefix directory does not exist at path: $Prefix"
            exit 1
        }
        $BuildDir = Join-Path -Path $Prefix -ChildPath "win64/$ReferencePlatform/$($packageVersion.ToString())"
    }

    # Create the build directory
    Create-Directory -Path $BuildDir

    # Set up the build directory structure:
    # / (root)
    # ├── build
    # ├── downloads
    # ├── release
    # ├── scripts
    # └── vcpkg

    Create-Directory -Path (Join-Path -Path $BuildDir -ChildPath "build")
    Create-Directory -Path (Join-Path -Path $BuildDir -ChildPath "downloads")
    Create-Directory -Path (Join-Path -Path $BuildDir -ChildPath "release")
    Create-Directory -Path (Join-Path -Path $BuildDir -ChildPath "scripts")
    Create-Directory -Path (Join-Path -Path $BuildDir -ChildPath "vcpkg")

    # Clone the vcpkg repository
    Clone-VcpkgRepository -DestinationFolder (Join-Path -Path $BuildDir -ChildPath "vcpkg")

    # Check if the reference platform manifest file exists
    if (-not (Test-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "vcpkg/$ReferencePlatform.json"))) {
        Write-Error "[build-win.ps1] Error: The vcpkg manifest file for reference platform $ReferencePlatform does not exist."
        exit 1
    }
    # Copy the vcpkg manifest file based on the reference platform version
    Copy-Item -Path (Join-Path -Path $PSScriptRoot -ChildPath "vcpkg/$ReferencePlatform.json") -Destination (Join-Path -Path $BuildDir -ChildPath "vcpkg/vcpkg.json") -Force

}


& $MainFunction