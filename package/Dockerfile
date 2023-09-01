# escape=`

# Use the latest Windows Server Core 2019 image
FROM mcr.microsoft.com/dotnet/framework/runtime:4.8-windowsservercore-ltsc2019

# Restore the default Windows shell for correct batch processing
SHELL ["cmd", "/S", "/C"]

RUN `
    # Download the Build Tools bootstrapper
    curl -SL --output vs_buildtools.exe https://aka.ms/vs/16/release/vs_buildtools.exe `
    `
    # Install Build Tools with the Microsoft.VisualStudio.Workload.AzureBuildTools workload, excluding workloads and components with known issues.
    && (start /w vs_buildtools.exe --quiet --wait --norestart --nocache `
        --installPath "%ProgramFiles(x86)%\Microsoft Visual Studio\2019\BuildTools" `
        --add Microsoft.VisualStudio.Workload.AzureBuildTools `
        --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended `
        --remove Microsoft.VisualStudio.Component.Windows10SDK.10240 `
        --remove Microsoft.VisualStudio.Component.Windows10SDK.10586 `
        --remove Microsoft.VisualStudio.Component.Windows10SDK.14393 `
        --remove Microsoft.VisualStudio.Component.Windows81SDK `
        || IF "%ERRORLEVEL%"=="3010" EXIT 0) `
    `
    # Cleanup
    && del /q vs_buildtools.exe

ENV TOOLS_DIR "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Auxiliary\\Build"

# Install Chocolatey
RUN powershell Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
RUN powershell choco install cmake -y --installargs 'ADD_CMAKE_TO_PATH=System'
RUN powershell choco install git -y

# Install vcpkg
ENV VCPKG_ROOT "C:\\vcpkg"
ENV VCPKG_TRIPLET "x64-windows"

RUN call "%TOOLS_DIR%\vcvars64.bat" `
    && git clone https://github.com/Microsoft/vcpkg.git `
    && "%VCPKG_ROOT%\bootstrap-vcpkg.bat" -disableMetrics

# Clone bookmarks
RUN git clone https://github.com/wgergely/bookmarks.git
ENV PACKAGE_DIR "C:\\bookmarks\\package"

# Build the vcpkg dependencies
RUN call "%TOOLS_DIR%\vcvars64.bat" `
    && "%VCPKG_ROOT%\vcpkg.exe" install `
        python3:%VCPKG_TRIPLET% `
        qt5[core,imageformats]:%VCPKG_TRIPLET% `
        ffmpeg[avcodec,avdevice,avfilter,avformat,avresample,bzip2,ffmpeg,fontconfig,freetype,lzma,opengl,swresample,swscale,x264,x265,zlib]:%VCPKG_TRIPLET% `
        openimageio[ffmpeg,freetype,gif,libheif,libraw,opencolorio,openjpeg,pybind11,tools,webp]:%VCPKG_TRIPLET% `
    --overlay-ports="%PACKAGE_DIR%\vcpkg_ports"

# Set up global variables to define the vcpkg installed package versions
# Extract and set Qt5 version components
RUN powershell -Command `
    "$qtVersion = (Get-Content ${VCPKG_ROOT}\\ports\\qt5\\vcpkg.json | ConvertFrom-Json).version; `
     $qtVersionParts = $qtVersion -split '\.'; `
     Set-Content -Path ${VCPKG_ROOT}\\qt_version_major.txt -Value $qtVersionParts[0]; `
     Set-Content -Path ${VCPKG_ROOT}\\qt_version_minor.txt -Value $qtVersionParts[1]; `
     Set-Content -Path ${VCPKG_ROOT}\\qt_version_patch.txt -Value $qtVersionParts[2]"

RUN setx QT_VERSION_MAJOR $(<${VCPKG_ROOT}\\qt_version_major.txt) /M `
    && setx QT_VERSION_MINOR $(<${VCPKG_ROOT}\\qt_version_minor.txt) /M `
    && setx QT_VERSION_PATCH $(<${VCPKG_ROOT}\\qt_version_patch.txt) /M

# ENV PATH="${PATH};${TOOLS_DIR};${VCPKG_ROOT}"

# # Set-up python disribution
# # Create the Python directory structure
# RUN mkdir "${PYTHON_DIR}" `
#     && mkdir "${PYTHON_DIR}/include" `
#     && mkdir "${PYTHON_DIR}/libs"


