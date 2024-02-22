$Global:ProgressPreference = 'SilentlyContinue';
$Global:ErrorActionPreference = 'Stop';

[string]$GIT_URL = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
[string]$GIT_SHA256 = "a6058d7c4c16bfa5bcd6fde051a92de8c68535fd7ebade55fc0ab1c41be3c8d5"
[string]$CMAKE_URL = "https://github.com/Kitware/CMake/releases/download/v3.28.3/cmake-3.28.3-windows-x86_64.msi"
[string]$CMAKE_SHA256 = "4ba223e3793e3770bfb046eb8c307d59feae2750f6f0bfb6445626d5cc75b2a6"

function Install-Software ([string]$name, [string]$url, [string]$checksum){
    # Get the exctension form the url by splittiung the url by '.' and taking the last element
    $extension = $url.Split('.')[-1];
    $installerPath = Join-Path "$env:TEMP" "$name-installer.$extension";

    Write-Host "[$name] Downloading installer...";
    Invoke-WebRequest -Uri $url -OutFile $installerPath;
    if (-not (Test-Path $installerPath)) {
        Write-Error "Failed to download $name from $url";
        exit 1;
    }

    Write-Host "[$name] Verifying checksum...";
    $actualChecksum = Get-FileHash -Path $installerPath -Algorithm "SHA256";
    if ($actualChecksum.Hash -ne $checksum) {
        Write-Error "$name Checksum verification failed: $actualChecksum.Hash != $checksum";
        exit 1;
    } else {
        Write-Host "[$name] Checksum is ok.";
    }
    
    Write-Host "[$name] Installing...";
    
    switch ($extension) {
        'exe' {
            Start-Process $installerPath -ArgumentList "/VERYSILENT /NORESTART" -Wait -NoNewWindow;
        }
        'msi' {
            if (-not (Test-Path "C:/cmake")) {
                New-Item -ItemType Directory -Path "C:/cmake" | Out-Null;
            }
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/i $installerPath INSTALL_ROOT=`"C:\\cmake`" ADD_CMAKE_TO_PATH=`"User`" ALLUSERS=2 MSIINSTALLPERUSER=1 /qn" -Wait -NoNewWindow;
        }
        'zip' {
            Expand-Archive -Path $installerPath -DestinationPath $env:ProgramFiles;
        }
        Default {
            Write-Error "Unsupported installer type: $extension";
            exit 1;
        }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install $name from $installerPath - $_";
        exit 1;
    }
    Write-Host "[$name] Installed successfully.";
    Remove-Item $installerPath -Force;
    Write-Host "[$name] Cleanup complete.";
}

Install-Software -name "git" -url $GIT_URL -checksum $GIT_SHA256;
Install-Software -name "cmake" -url $CMAKE_URL -checksum $CMAKE_SHA256;