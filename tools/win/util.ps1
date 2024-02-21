
function Get-SourceVersion {
    $PathToInitPy = Join-Path -Path $PSScriptRoot -ChildPath "../../bookmarks/__init__.py"
    
    # Ensure __init__.py exists
    if (!(Test-Path -Path $PathToInitPy)) {
        Write-Message -t "error" "Unable to locate the __init__.py file at path: $PathToInitPy"
        exit 1
    }
    # Read __init__.py's contents
    $fileContents = Get-Content -Path $PathToInitPy
    if ($null -eq $fileContents) {
        Write-Message -t "error" "Failed to read the contents of __init__.py."
        exit 1
    }

    # Search for the __version__ variable
    $versionLine = $fileContents | Where-Object { $_ -match "__version__.*=.*['`"][v]*(.*)['`"]" }
    if ($null -eq $versionLine) {
        Write-Message -t "error" "Version information not found in __init__.py."
        exit 1
    }

    # Cast to [version] type
    try {
        [version]$version = $Matches[1]
        Write-Message -m "Source version: $($version.ToString())"
        return $version
    }
    catch {
        Write-Message -t "error" "Version found but failed to cast string to [version] type: $_"
        exit 1
    }
}


function New-Directory {
    param (
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        Write-Message -m "Creating directory $Path"
        New-Item -ItemType Directory -Path $Path | Out-Null
        if (-not (Test-Path $Path)) {
            Write-Message -t "error" "Failed to create the directory at $Path"
            exit 1
        }
    }
}


function Remove-Directory {
    param (
        [string]$Path
    )

    if (Test-Path $Path) {
        Write-Message -m "Deleting directory $Path"
        Remove-Item -Recurse -Force $Path
        if (Test-Path $Path) {
            Write-Message -t "error" "Failed to delete the directory at path: $Path"
            exit 1
        }
    }
}

function Write-Message{
    param(
        [Parameter(Mandatory=$true)]
        [Alias("m")]
        [string]$Message,

        [ValidateSet("info", "warning", "error")]
        [Alias("t")]
        [string]$Type = "info",
        
        [Alias("n" )]
        [switch]$NoPrefix = $false
    )

    if ($global:BuildVerbosity -eq "silent") {
        return
    }

    if ($Message -eq "") {
        return
    }

    if (-not $NoPrefix) {
        $Message = "[build] $Message"
    }

    # Write the message
    switch ($Type) {
        "info" {
            Write-Host $Message
        }
        "warning" {
            Write-Warning $Message
        }
        "error" {
            Write-Error $Message
        }
    }
}