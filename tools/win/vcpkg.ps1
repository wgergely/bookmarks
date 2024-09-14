. "$PSScriptRoot/util.ps1"
. "$PSScriptRoot/buildtool.ps1"

function Get-Vcpkg
{
    param (
        [Parameter(Mandatory = $true)]
        [Alias("p")]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [Alias("r")]
        [bool]$Reset
    )

    Set-Location -Path $Path

    if ($Reset)
    {
        Write-Message -m "Cleaning vcpkg directory..."
        if (Test-Path -Path (Join-Path -Path $Path -ChildPath "vcpkg"))
        {
            # cd to the build directory prior to delete
            Remove-Directory -Path (Join-Path -Path $Path -ChildPath "vcpkg")

            if ($LASTEXITCODE -ne 0)
            {
                Write-Message -t "error" "Failed to delete the vcpkg directory."
                exit 1
            }

            # Fail if the directory still exists
            if (Test-Path -Path (Join-Path -Path $Path -ChildPath "vcpkg"))
            {
                Write-Message -t "error" "Failed to delete the vcpkg directory."
                exit 1
            }
        }
    }
    else
    {
        if (Test-Path -Path (Join-Path -Path $Path -ChildPath "vcpkg"))
        {
            # Check if vcpkg has been already bootstrapped (vcpkg.exe exists)
            if (-not (Test-Path -Path (Join-Path -Path $Path -ChildPath "vcpkg/vcpkg.exe")))
            {
                Write-Message -m "vcpkg directory exists, but it is not bootstrapped. Deleting the directory..."

                Remove-Directory -Path (Join-Path -Path $Path -ChildPath "vcpkg")

                # Fail if the directory still exists
                if (Test-Path -Path (Join-Path -Path $Path -ChildPath "vcpkg"))
                {
                    Write-Message -t "error" "Failed to delete the vcpkg directory."
                    exit 1
                }
            }
            else
            {
                Write-Message -m "vcpkg directory exists and is bootstrapped. Skipping cloning."
                return
            }
        }
    }

    Write-Message -m "Cloning vcpkg repository to $Path"
    git clone https://github.com/microsoft/vcpkg.git $Path/vcpkg

    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to clone the vcpkg repository."
        exit 1
    }

    if (-not (Test-Path -Path (Join-Path -Path $Path -ChildPath "vcpkg")))
    {
        Write-Message -t "error" "Failed to clone the vcpkg repository."
        exit 1
    }

    Write-Message -m "Bootstrapping vcpkg..."
    $vcpkgPath = Join-Path -Path $Path -ChildPath "vcpkg"
    $vcpkgExePath = Join-Path -Path $vcpkgPath -ChildPath "vcpkg.exe"
    $vcpkgBootstrapperPath = Join-Path -Path $vcpkgPath -ChildPath "bootstrap-vcpkg.bat"

    if (-not (Test-Path -Path $vcpkgBootstrapperPath))
    {
        Write-Message -t "error" "bootstrap-vcpkg.bat not found at path: $vcpkgBootstrapperPath"
        exit 1
    }

    # Run the bootstrapper
    & $vcpkgBootstrapperPath -disableMetrics
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to bootstrap vcpkg."
        exit 1
    }

    if (-not (Test-Path -Path $vcpkgExePath))
    {
        Write-Message -t "error" "vcpkg.exe not found at path: $vcpkgExePath"
        exit 1
    }
}

function Copy-VcpkgManifest
{
    param (
        [Parameter(Mandatory = $true)]
        [Alias("r")]
        [string]$ReferencePlatform,

        [Parameter(Mandatory = $true)]
        [Alias("p")]
        [string]$Path
    )

    # The manifest files are located in ../config relative to the script folder
    # We'll need to find CY[0-9]{4}.json and copy it to $Path/vcpkg.json
    $manifestsDir = Join-Path -Path $PSScriptRoot -ChildPath "../config"

    # Check if the folder exists
    if (-not (Test-Path -Path $manifestsDir))
    {
        Write-Message -t "error" "The config folder does not exist."
        exit 1
    }

    # Find the appropriate manifest file
    $manifestFile = Get-ChildItem -Path $manifestsDir -Filter "$ReferencePlatform.json" -Recurse
    if ($null -eq $manifestFile)
    {
        Write-Message -t "error" "The vcpkg manifest file for reference platform $ReferencePlatform does not exist."
        exit 1
    }

    # Copy the manifest file to the build directory
    Write-Message -m "Copying the vcpkg manifest file to $Path/vcpkg/vcpkg.json"
    Copy-Item -Path $manifestFile.FullName -Destination (Join-Path -Path $Path -ChildPath "vcpkg/vcpkg.json")
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to copy the vcpkg manifest file."
        exit 1
    }

    # Check if the manifest file is a valid json
    $manifestContent = Get-Content -Path (Join-Path -Path $Path -ChildPath "vcpkg/vcpkg.json")
    try
    {
        $manifestContent | ConvertFrom-Json
    }
    catch
    {
        Write-Message -t "error" "The vcpkg manifest file is not a valid json."
        exit 1
    }
}

function Patch-VcpkgTriplet
{
    param (
        [Parameter(Mandatory = $true)]
        [Alias("r")]
        [string]$ReferencePlatform,

        [Parameter(Mandatory = $true)]
        [Alias("p")]
        [string]$Path
    )

    # We want to add set(VCPKG_PLATFORM_TOOLSET v{version}) to the ./triplets/x64-windows.cmake file
    $tripletFile = Join-Path -Path $Path -ChildPath "vcpkg/triplets/x64-windows.cmake"

    if (-not (Test-Path -Path $tripletFile))
    {
        Write-Message -t "error" "The x64-windows.cmake file does not exist."
        exit 1
    }

    # Read the file contents
    $tripletContent = Get-Content -Path $tripletFile
    if ($null -eq $tripletContent)
    {
        Write-Message -t "error" "The x64-windows.cmake file is empty."
        exit 1
    }

    # Check if the file already contains the VCPKG_PLATFORM_TOOLSET
    if ($tripletContent -match "set\(VCPKG_PLATFORM_TOOLSET v[0-9]+\.[0-9]+\)")
    {
        Write-Message -m "The x64-windows.cmake file already contains VCPKG_PLATFORM_TOOLSET."
        return
    }

    # Find the version of the Visual Studio build tools
    Verify-ReferencePlatformArg -r $ReferencePlatform
    $ReferencePlatforms = Get-ReferencePlatforms

    $toolset_version = $ReferencePlatforms.$ReferencePlatform.vs_toolset

    # Add the VCPKG_PLATFORM_TOOLSET to the file
    Write-Message -m "Adding VCPKG_PLATFORM_TOOLSET to x64-windows.cmake file."
    $tripletContent += "`nset(VCPKG_PLATFORM_TOOLSET $toolset_version)"
    Set-Content -Path $tripletFile -Value $tripletContent
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to write to the x64-windows.cmake file."
        exit 1
    }

    Write-Message -m "Successfully patched the x64-windows.cmake file."
}


function Install-VcpkgPackages
{
    param(
        [Parameter(Mandatory = $true)]
        [Alias("p")]
        [string]$Path
    )

    Write-Message -m "Installing vcpkg packages..."

    # Change to the vcpkg directory
    Set-Location -Path (Join-Path -Path $Path -ChildPath "vcpkg")

    # Install the packages
    ./vcpkg.exe install --triplet x64-windows
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to install vcpkg packages."
        exit 1
    }
}

function Get-VcpkgInfo
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Package
    )

    $vcpkgInstallDir = Join-Path -Path $Path -ChildPath "vcpkg/vcpkg_installed"
    if (-not (Test-Path -Path $vcpkgInstallDir))
    {
        Write-Message -t "error" "The vcpkg_installed folder does not exist."
        exit 1
    }

    # Read the vcpkg/info/*.list file
    $infoFiles = Get-ChildItem -Path "$vcpkgInstallDir/vcpkg/info" -Filter "*.list" -Recurse
    if ($null -eq $infoFiles)
    {
        Write-Message -t "error" "The info folder does not exist. Was looking in $vcpkgInstallDir/vcpkg/info."
        exit 1
    }

    # Find the list file.
    $listFile = $infoFiles | Where-Object { $_ -match "^$Package.*\.list" }
    if ($null -eq $listFile)
    {
        Write-Message -t "error" "Could not find the "$Package" list file."
        exit 1
    }

    # Ensure $listFile is an array
    if ($listFile -is [string])
    {
        $listFile = @($listFile)
    }

    # Use only the first result if one or more items are found
    if ($listFile.Count -gt 0)
    {
        $listFile = $listFile[0]
    }
    else
    {
        Write-Message -t "error" "Could not find the $Package list file."
        exit 1
    }

    # Read the file contents
    $listFilePath = Join-Path -Path $vcpkgInstallDir -ChildPath "vcpkg/info/$listFile"

    try
    {
        Write-Message -m "Reading $Package list file ($listFile)"
        $fileContents = Get-Content -Path $listFilePath
    }
    catch
    {
        Write-Message -t "error" "Failed to read the $Package list file."
        exit 1
    }

    if ($null -eq $fileContents)
    {
        Write-Message -t "error" "The $Package list file is empty."
        exit 1
    }

    return $fileContents
}



function Get-Version
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ReferencePlatform,

        [Parameter(Mandatory = $true)]
        [string]$Package

    )

    $manifestsDir = Join-Path -Path $PSScriptRoot -ChildPath "../config"

    if (-not (Test-Path -Path $manifestsDir))
    {
        Write-Message -t "error" "$manifestsDir does not exist."
        exit 1
    }

    $manifestFile = Get-ChildItem -Path $manifestsDir -Filter "$ReferencePlatform.json" -Recurse

    if ($null -eq $manifestFile)
    {
        Write-Message -t "error" "The vcpkg manifest file for reference platform $ReferencePlatform does not exist (was looking in $manifestsDir)."
        exit 1
    }

    # Make sure we only found 1 file

    # Read the file contents
    try
    {
        $manifestContents = Get-Content -Path $manifestFile.FullName -Raw | ConvertFrom-Json
        if ($null -eq $manifestContents)
        {
            Write-Message -t "error" "The vcpkg manifest file is empty."
            exit 1
        }
    }
    catch
    {
        Write-Message -t "error" "Failed to read the vcpkg manifest file."
        exit 1
    }

    # Parse the qt version
    $overrides = $manifestContents.overrides
    if ($null -eq $overrides)
    {
        Write-Message -t "error" "The overrides section missing in the manifest file."
        exit 1
    }

    # Iterate over each override item
    foreach ($override in $overrides)
    {
        if ($override.Name -match ".*$Package.*")
        {

            $version = $override.Version
            if ($null -eq $version)
            {
                Write-Message -t "error" "$( $override.Name ) is found but version is not defined in manifest file."
                exit 1
            }

            try
            {
                $MAJOR_VERSION = $version.Split(".")[0]
                $MINOR_VERSION = $version.Split(".")[1]
                $PATCH_VERSION = $version.Split(".")[2].Split("#")[0]

                return @{
                    "MAJOR_VERSION" = $MAJOR_VERSION
                    "MINOR_VERSION" = $MINOR_VERSION
                    "PATCH_VERSION" = $PATCH_VERSION
                }
            }
            catch
            {
                Write-Message -t "error" "Failed to parse $Package version: $_"
                exit 1
            }
        }
    }

    return $null
}