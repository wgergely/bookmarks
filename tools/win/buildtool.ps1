. "$PSScriptRoot/util.ps1"

function Get-ReferencePlatforms
{
    # Ensure configuration file exists
    $config = Join-Path -Path $PSScriptRoot -ChildPath "../config/referenceplatform.json"

    if (Test-Path $config)
    {
        Write-Message -m "Found config: $config"
    }
    else
    {
        Write-Message -t "error" "$config not found at path: $config"
        exit 1
    }

    # Verify data in the JSON file is valid
    try
    {
        $json = Get-Content -Path $config -Raw | ConvertFrom-Json
    }
    catch
    {
        Write-Message -t "error" "Failed to parse $config. Ensure it is valid JSON."
        exit 1
    }
    # Ensure the JSON file contains expected keys in the format of CY[0-9]{4}
    $json.PSObject.Properties.Name | ForEach-Object {
        if ($_ -notmatch '^CY[0-9]{4}.*$')
        {
            Write-Message -t "error" "Invalid reference platform name '$_' in $config. Must be in the format of CY[0-9]{4}.*."
            exit 1
        }
    }

    # Ensure each CY version contains the expected keys
    $json.PSObject.Properties.Value | ForEach-Object {
        if (-Not $_.PSObject.Properties.Name.Contains("vs_year"))
        {
            Write-Message -t "error" "Missing 'vs_year' key in $config for reference platform $_."
            exit 1
        }
        if (-Not $_.PSObject.Properties.Name.Contains("vs_min"))
        {
            Write-Message -t "error" "Missing 'vs_min' key in $config for reference platform $_."
            exit 1
        }
        if (-Not $_.PSObject.Properties.Name.Contains("vs_max"))
        {
            Write-Message -t "error" "Missing 'vs_max' key in $config for reference platform $_."
            exit 1
        }
        if (-Not $_.PSObject.Properties.Name.Contains("vs_version"))
        {
            Write-Message -t "error" "Missing 'vs_version' key in $config for reference platform $_."
            exit 1
        }
        if (-Not $_.PSObject.Properties.Name.Contains("vs_url"))
        {
            Write-Message -t "error" "Missing 'vs_url' key in $config for reference platform $_."
            exit 1
        }
        if (-Not $_.PSObject.Properties.Name.Contains("vs_toolset"))
        {
            Write-Message -t "error" "Missing 'vs_toolset' key in $config for reference platform $_."
            exit 1
        }
    }

    # Read and convert the JSON file to a PowerShell object
    $jsonObject = Get-Content -Path $config -Raw | ConvertFrom-Json

    # Cast the vs_min and vs_max values to [version] type
    try
    {
        $jsonObject.PSObject.Properties.Value | ForEach-Object {
            $_.vs_min = [version]$_.vs_min
            $_.vs_max = [version]$_.vs_max
        }
    }
    catch
    {
        Write-Message -t "error" "type."
        exit 1
    }

    return $jsonObject
}


function Verify-ReferencePlatformArg
{
    param(
        [Parameter(Mandatory = $true, HelpMessage = "Reference Platform name (for example, CY2022)")]
        [Alias("r")]
        [string]$ReferencePlatform
    )

    $referencePlatforms = Get-ReferencePlatforms
    $validReferencePlatforms = $referencePlatforms.PSObject.Properties.Name

    if ($validReferencePlatforms -notcontains $ReferencePlatform)
    {
        Write-Message -t "error" "Invalid reference platform name '$ReferencePlatform'. Must be one of: $validReferencePlatforms."
        exit 1
    }
}


function Find-BuildTools
{
    param(
        [Parameter(Mandatory = $true, HelpMessage = "Reference Platform name (for example, CY2022)")]
        [Alias("r")]
        [string]$ReferencePlatform
    )

    Verify-ReferencePlatformArg -r $ReferencePlatform
    $referencePlatforms = Get-ReferencePlatforms

    $vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    Write-Message -m "Looking for Visual Studio build tools using $vsWhere"

    if (-not (Test-Path $vsWhere))
    {
        Write-Message -t "warning" "$vsWhere was not found."
        return ""
    }

    # Find all installed Visual Studio instances that have the required VC tools
    $vsInstances = & $vsWhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json
    if ($vsInstances.Count -eq 0)
    {
        Write-Message -t "warning" "No Visual Studio instances found with the required VC tools."
        return ""
    }

    $compatibleVSInstance = $null
    foreach ($instance in $vsInstances)
    {
        $instanceVersion = New-Object Version $instance.installationVersion
        if ($instanceVersion -ge $referencePlatforms.$ReferencePlatform.vs_min -and $instanceVersion -lt $referencePlatforms.$ReferencePlatform.vs_max)
        {
            $compatibleVSInstance = $instance
            break
        }
    }

    if ($null -eq $compatibleVSInstance)
    {
        [string]$minVersion = $referencePlatforms.$ReferencePlatform.vs_min.ToString()
        [string]$maxVersion = $referencePlatforms.$ReferencePlatform.vs_max.ToString()
        [string]$foundVersions = $vsInstances.installationVersion -join ", "
        Write-Message -t "error" "Couldn't find a compatible Visual Studio version for reference platform $ReferencePlatform (was expecting >$minVersion and <$maxVersion but found $( $foundVersions ))."
        return ""
    }
    else
    {
        Write-Message -m "Reference Platform $ReferencePlatform`: Found Visual Studio $( $compatibleVSInstance.installationVersion )"
    }

    $vsPath = $compatibleVSInstance.installationPath
    $vcVars64 = "$vsPath\VC\Auxiliary\Build\vcvars64.bat"
    if (-not (Test-Path $vcVars64))
    {
        Write-Message -t "error" "`vcvars64.bat` not found in detected Visual Studio path."
        return ""
    }
    else
    {
        Write-Message -m "Found $vcVars64"
    }

    # Return the path to vcvars64.bat
    return $vcVars64
}


function Ensure-Tool
{
    param(
        [Parameter(Mandatory = $true, HelpMessage = "Tool name (for example, Git)")]
        [Alias("t")]
        [string]$Tool
    )

    try
    {
        # Attempt to execute '$Tool --version' and capture its output
        $Version = & $Tool --version 2>&1
        Write-Message -m "Found $Tool - $Version"
    }
    catch
    {
        # An error occurred, likely because the tool is not installed or not in PATH
        Write-Message -t "error" "$Tool not found. Ensure $Tool is available in the PATH."
        exit 1
    }
}



function Install-BuildTools
{
    param(
        [Parameter(Mandatory = $true, HelpMessage = "Reference Platform name (e.g. CY2022)")]
        [Alias("r")]
        [string]$ReferencePlatform
    )

    Verify-ReferencePlatformArg -r $ReferencePlatform
    $referencePlatforms = Get-ReferencePlatforms

    # Download the Build Tools bootstrapper
    $installer = Join-Path -Path $env:TEMP -ChildPath "vs_buildtools_$( $referencePlatforms.$referencePlatform.vs_year ).exe"

    if (Test-Path -Path $installer)
    {
        Write-Message -m "Removing existing Visual Studio Build Tools installer at $installer"
        Remove-Item -Path $installer -Force
        if (Test-Path -Path $installer)
        {
            Write-Message -t "error" "Failed to remove existing Visual Studio Build Tools installer at $installer."
            exit 1
        }
    }

    Write-Message -m "Downloading $( $referencePlatforms.$referencePlatform.vs_url ) to $installer"

    Invoke-WebRequest -Uri $referencePlatforms.$referencePlatform.vs_url -OutFile $installer
    if (-not (Test-Path -Path $installer))
    {
        Write-Message -t "error" "File not found at path: $installer. Failed to download the Visual Studio Build Tools installer."
        exit 1
    }

    # Install Build Tools with specified workloads and components, excluding those with known issues
    $installPath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\$( $referencePlatforms.$referencePlatform.vs_year )\BuildTools"
    $arguments = @(
        "--quiet",
        "--wait",
        "--norestart",
        "--nocache",
        "--installPath `"$installPath`"",
        "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended",
        "--add Microsoft.VisualStudio.Component.VC.ATL",
        "--remove Microsoft.VisualStudio.Component.Windows10SDK.10240",
        "--remove Microsoft.VisualStudio.Component.Windows10SDK.10586",
        "--remove Microsoft.VisualStudio.Component.Windows10SDK.14393",
        "--remove Microsoft.VisualStudio.Component.Windows81SDK"
    )

    Write-Message -m "Installing Visual Studio Build Tools to $installPath"
    $process = Start-Process -FilePath "$installer" -ArgumentList $arguments -Wait -PassThru

    # Check for reboot required (exit code 3010)
    if ($process.ExitCode -eq 3010)
    {
        Write-Message -m "Installation completed successfully, but a reboot is required."
    }
    elseif ($process.ExitCode -ne 0)
    {
        Write-Message -m "Installation failed with exit code $( $process.ExitCode )."
    }
    else
    {
        Write-Message -m "Installation completed successfully with exit code $( $process.ExitCode )."
    }

    # Cleanup
    Remove-Item -Path "$installer" -Force
}


function Set-EnvironmentForBuild
{
    param(
        [Parameter(Mandatory = $true, HelpMessage = "Path to vcvars64.bat")]
        [Alias("f")]
        [string]$file
    )

    if (-not (Test-Path -Path $file))
    {
        Write-Message -t "error" "vcvars64.bat not found at path: $file"
        exit 1
    }

    Write-Message -m "Setting up the environment for building with Visual Studio..."
    # We'll have to invoke the bat file in cmd and save the environment variables to a temp file
    $tempFile = [System.IO.Path]::GetTempFileName()
    cmd.exe /c "call `"$file`" && set" > $tempFile

    # Check errors
    if ($LASTEXITCODE -ne 0)
    {
        Write-Message -t "error" "Failed to set up the environment for building with Visual Studio."
        exit 1
    }

    # Read the environment variables from the temp file and set them in the current session
    Get-Content -Path $tempFile | ForEach-Object {
        if ($_ -match '^(.+?)=(.*)$')
        {
            [string]$name = $matches[1]
            [string]$value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value, [System.EnvironmentVariableTarget]::Process)
        }
    }

    # Remove the temporary file after use
    Remove-Item -Path $tempFile
}


function Main
{
    [string] $vcVars64 = Find-BuildTools
    if ($vcVars64 -eq "")
    {
        Write-Message -t "error" "Visual Studio build tools not found."
        exit 1
    }
}