param (
    [Parameter(Mandatory = $true, HelpMessage = "Enter the Reference Platform name (e.g. CY2022).")]
    [Alias("r")]
    [string]$ReferencePlatform,
    
    [Parameter(HelpMessage = "Optional build folder. If not provided, the default directory is C:\build\{ReferencePlatform}-{Version}.")]
    [Alias("b")]
    [string]$BuildDir = "",

    # Reset flags
    [Parameter(HelpMessage = "Reset the vcpkg build step")]
    [Alias("rv")]
    [switch]$ResetVcpkg = $false,

    [Parameter(HelpMessage = "Reset the pyside build step")]
    [Alias("rp")]
    [switch]$ResetPySide = $false,

    [Parameter(HelpMessage = "Reset the app build step")]
    [Alias("ra")]
    [switch]$ResetApp = $false,

    [Parameter(HelpMessage = "Reset the dist build step")]
    [Alias("rd")]
    [switch]$ResetDist = $false,

    [Parameter(HelpMessage = "Reset the installer build step")]
    [Alias("ri")]
    [switch]$ResetInstaller = $false,    

    # Skip flags
    [Parameter(HelpMessage = "Skip the vcpkg build.")]
    [Alias("sv")]
    [switch]$SkipVcpkg = $false,

    [Parameter(HelpMessage = "Skip the pyside build.")]
    [Alias("sp")]
    [switch]$SkipPySide = $false,

    [Parameter(HelpMessage = "Skip the app libraries.")]
    [Alias("sa")]
    [switch]$SkipApp = $false,
    
    [Parameter(HelpMessage = "Skip the dist build.")]
    [Alias("sd")]
    [switch]$SkipDist = $false,

    [Parameter(HelpMessage = "Skip installer.")]
    [Alias("si")]
    [switch]$SkipInstaller = $false,

    [Parameter(HelpMessage = "Verbosisty")]
    [Alias("v")]
    [ValidateSet("silent", "normal", "verbose")]
    [string]$Verbosity = "normal"
)

. "$PSScriptRoot/win/util.ps1"
. "$PSScriptRoot/win/buildtool.ps1"
. "$PSScriptRoot/win/vcpkg.ps1"
. "$PSScriptRoot/win/pyside.ps1"
. "$PSScriptRoot/win/app.ps1"
. "$PSScriptRoot/win/dist.ps1"
. "$PSScriptRoot/win/installer.ps1"


function Save-Environment {
    # Create a new global hashtable to store environment variables
    $global:SavedEnv = @{}
    $global:SavedCwd = Get-Location

    # Map the verbosity to msbuild's -verbosity flag
    switch ($Verbosity) {
        "silent" {
            $global:MSBuildVerbosity = "quiet"
        }
        "normal" {
            $global:MSBuildVerbosity = "minimal"
        }
        "verbose" {
            $global:MSBuildVerbosity = "normal"
        }
    }

    # Map the verbosity to the cmake --log-level flag
    switch ($Verbosity) {
        "silent" {
            $global:CMakeVerbosity = "ERROR"
        }
        "normal" {
            $global:CMakeVerbosity = "WARNING"
        }
        "verbose" {
            $global:CMakeVerbosity = "STATUS"
        }
    }

    # Capture and store all current environment variables
    Get-ChildItem -Path Env: | ForEach-Object {
        $global:SavedEnv[$_.Name] = $_.Value
    }
}


function Restore-Environment {
    if ($null -eq $global:SavedCwd) {
        Write-Message -t "warning" -m "No current working directory was saved to restore."
    }
    else {
        Set-Location -Path $global:SavedCwd
    }

    if ($null -eq $global:SavedEnv) {
        Write-Message -t "warning" -m "No environment was saved to restore."
        return
    }
    else {
        # Restore saved environment variables
        foreach ($key in $global:SavedEnv.Keys) {
            [System.Environment]::SetEnvironmentVariable($key, $global:SavedEnv[$key], [System.EnvironmentVariableTarget]::Process)
        }

        # Identify and remove any variables that were added after Save-Environment was called
        $currentVars = Get-ChildItem -Path Env: | ForEach-Object { $_.Name }
        $varsToRemove = $currentVars | Where-Object { $global:SavedEnv.ContainsKey($_) -eq $false }

        foreach ($var in $varsToRemove) {
            [System.Environment]::SetEnvironmentVariable($var, $null, [System.EnvironmentVariableTarget]::Process)
        }
    }
}

function MainFunction {
    Write-Message -n -m "`n=======================`nEnvironment`n======================="

    # Verify the reference platform argument
    Verify-ReferencePlatformArg -r $ReferencePlatform

    Write-Message -m "Reference Platform: $ReferencePlatform"

    [string]$vcVars64 = Find-BuildTools -r $ReferencePlatform
    if ($vcVars64 -eq "") {
        Write-Message -m "Visual Studio build tools not found, installing build tools..."
        Install-BuildTools -r $ReferencePlatform
        [string]$vcVars64 = Find-BuildTools -r $ReferencePlatform
        if ($vcVars64 -eq "") {
            Write-Message -t "error" "Failed to install build tools."
            exit 1
        }
    }

    # Set up the environment for building with Visual Studio
    Set-EnvironmentForBuild -f $vcVars64

    Ensure-Tool -t "git"
    Ensure-Tool -t "cmake"

    # Get the source version __init__.py
    $packageVersion = Get-SourceVersion

    # Set default build directory if not provided
    if ($BuildDir -eq "") {
        [string]$BuildDir = "C:\build\$ReferencePlatform"
    }
    else {
        [string]$BuildDir = $BuildDir.TrimEnd("\").TrimEnd("/") + "\" + "$ReferencePlatform-$packageVersion"
    }
    
    New-Directory -Path $BuildDir
    
    # vcpkg
    Write-Message -n -m "`n=======================`nvcpkg`n======================="
    if (-not $SkipVcpkg) {

        Set-Location -Path $BuildDir

        New-Directory -Path (Join-Path -Path $BuildDir -ChildPath "vcpkg")
        Get-Vcpkg -Path $BuildDir -ReferencePlatform $ReferencePlatform -Reset $ResetVcpkg
        Copy-VcpkgManifest -ReferencePlatform $ReferencePlatform -Path $BuildDir

        Install-VcpkgPackages -Path $BuildDir
    }
    else {
        Write-Message -t "warning" -m "Skipping vcpkg build."
    }

    # pyside
    Write-Message -n -m "`n=======================`nPySide`n======================="
    if (-not $SkipPySide) {

        Set-Location -Path $BuildDir
        
        New-Directory -Path (Join-Path -Path $BuildDir -ChildPath "python")
        New-Directory -Path (Join-Path -Path $BuildDir -ChildPath "pyside")
        New-Directory -Path (Join-Path -Path $BuildDir -ChildPath "libclang")
        
        # Package Python
        New-PythonDistribution -Path $BuildDir -ReferencePlatform $ReferencePlatform -Reset $ResetPySide
        
        # Get libclang
        Set-Location -Path $BuildDir
        Get-LibClang -Path $BuildDir -ReferencePlatform $ReferencePlatform
        Set-Location -Path $BuildDir
        Get-PySide -Path $BuildDir -ReferencePlatform $ReferencePlatform -Reset $ResetPySide
        Set-Location -Path $BuildDir
        Build-PySide -Path $BuildDir -ReferencePlatform $ReferencePlatform -Reset $ResetPySide
    }
    else {
        Write-Message -t "warning" -m "Skipping PySide build."
    }

    # app
    Write-Message -n -m "`n=======================`nApp`n======================="
    if (-not $SkipApp) {

        Set-Location -Path $BuildDir

        Build-App -Path $BuildDir -ReferencePlatform $ReferencePlatform -Version $packageVersion -Reset $ResetApp
    }
    else {
        Write-Message -t "warning" -m "Skipping App build."
    }

    # dist
    Write-Message -n -m "`n=======================`nDist`n======================="
    if (-not $SkipDist) {

        Set-Location -Path $BuildDir
        Build-Dist -Path $BuildDir -ReferencePlatform $ReferencePlatform -Version $packageVersion -Reset $ResetDist
    }
    else {
        Write-Message -t "warning" -m "Skipping Dist build."
    }

    #installer
    Write-Message -n -m "`n=======================`nInstaller`n======================="
    if (-not $SkipInstaller) {

        Set-Location -Path $BuildDir
        Build-Installer -Path $BuildDir -ReferencePlatform $ReferencePlatform -Version $packageVersion -Reset $ResetInstaller
    }
    else {
        Write-Message -t "warning" -m "Skipping Installer build."
    }

}


# Get the current value of the $ProgressPreference variable
$_currentProgressPreference = $global:ProgressPreference
$global:ProgressPreference = "SilentlyContinue"

try {

    Write-Message -m "Saving environment variables."
    Save-Environment

    Write-Message -m "Starting build process."

    # Set the TMPDIR and TEMP environment variables to C:\temp to avoid path length issues
    [System.Environment]::SetEnvironmentVariable("TMPDIR", "C:\temp", [System.EnvironmentVariableTarget]::Process)
    [System.Environment]::SetEnvironmentVariable("TEMP", "C:\temp", [System.EnvironmentVariableTarget]::Process)

    if (-not (Test-Path -Path "C:\temp")) {
        New-Item -Path "C:\temp" -ItemType "directory" | Out-Null
    }

    MainFunction

    Write-Message -m "Build finished."
}
finally {
    Set-Location -Path $BuildDir
    Write-Message -m "Restoring environment variables."
    Restore-Environment

    $global:ProgressPreference = $_currentProgressPreference
}