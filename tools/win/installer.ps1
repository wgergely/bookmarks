function Build-Installer
{
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ReferencePlatform,

        [Parameter(Mandatory = $true)]
        [string]$Version,

        [Parameter(Mandatory = $true)]
        [bool]$Reset
    )

    Verify-ReferencePlatformArg -r $ReferencePlatform

    # Set up directory structure
    $buildDir = Join-Path -Path $Path -ChildPath "dist/$($Version.ToString() )"
    $installerFile = Join-Path -Path $buildDir -ChildPath "dist/Bookmarks_$( $ReferencePlatform )_v$($Version.ToString() ).exe"

    if (Test-Path -Path $installerFile)
    {
        Write-Message -t "warning" -m "$installerFile already exists. Removing."
        Remove-Item -Path $installerFile -Force
    }

}