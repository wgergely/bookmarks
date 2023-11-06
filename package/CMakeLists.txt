cmake_minimum_required(VERSION 3.20)

project(
	Bookmarks
	VERSION 0.9.1
	DESCRIPTION "Bookmarks is a lightweight asset manager for digital artists working in the animation, motion graphics and VFX industries."
	HOMEPAGE_URL "https://bookmarks-vfx.com"
)

if(NOT WIN32)
    message(
        FATAL_ERROR
        "No package exists for ${CMAKE_SYSTEM_NAME} systems just yet.\n"
        "Please visit https://github.com/wgergely/bookmarks/issues/1 to request a package for your platform."
    )
endif()

if(WIN32 AND NOT MSVC)  
    message(FATAL_ERROR "Check your compiler against the VFX Reference Platform (only Visual Studio is supported).")
endif()
if (NOT CMAKE_GENERATOR MATCHES "Visual Studio.*")
        message(WARNING "Build only supports Visual Studio generators")
    endif()
if (NOT CMAKE_GENERATOR_PLATFORM STREQUAL "x64")
	message(FATAL_ERROR "Build only supports x64")
endif()



set(CMAKE_CXX_STANDARD 14)
set_property(GLOBAL PROPERTY USE_FOLDERS On)

include(cmake/config.cmake)
include(cmake/port_versions.cmake)

get_archives()

# vcpkg
add_custom_command(
  OUTPUT ${PACKAGES_DIR}/vcpkg/vcpkg.exe
  WORKING_DIRECTORY ${PACKAGES_DIR}/vcpkg
  COMMAND ${PACKAGES_DIR}/vcpkg/bootstrap-vcpkg.bat
)
add_custom_target(
  vcpkg-bootstrap ALL
  DEPENDS ${PACKAGES_DIR}/vcpkg/vcpkg.exe
)


# vcpkg-python	
get_python_version()
set(PYTHON_LIST_FILE ${PACKAGES_DIR}/vcpkg/installed/vcpkg/info/python${PYTHON_VERSION_MAJOR}_${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}.${PYTHON_VERSION_PATCH}_${VCPKG_TRIPLET}.list)
add_custom_command(
	OUTPUT ${PYTHON_LIST_FILE}
	COMMAND echo "Building Python..."
	COMMAND ${PACKAGES_DIR}/vcpkg/vcpkg.exe install python3:${VCPKG_TRIPLET} --overlay-ports="${VCPKG_OVERLAYS_DIR}"
)
add_custom_target(
	vcpkg-python ALL
	DEPENDS ${PYTHON_LIST_FILE}
)
add_dependencies(vcpkg-python vcpkg-bootstrap)
	
# vcpkg-qt
get_qt_version()
set(QT_LIST_FILE ${PACKAGES_DIR}/vcpkg/installed/vcpkg/info/qt${QT_VERSION_MAJOR}-base_${QT_VERSION_MAJOR}.${QT_VERSION_MINOR}.${QT_VERSION_PATCH}_${VCPKG_TRIPLET}.list)
add_custom_command(
	OUTPUT ${QT_LIST_FILE}
	COMMAND echo.
	COMMAND echo "vcpkg is building Qt"
	COMMAND ${PACKAGES_DIR}/vcpkg/vcpkg.exe install qt5[core,imageformats]:${VCPKG_TRIPLET} --overlay-ports=${VCPKG_OVERLAYS_DIR}
	COMMAND echo "vcpkg finished building Qt"
	COMMAND echo.
)
add_custom_target(
	vcpkg-qt ALL
	DEPENDS ${QT_LIST_FILE}
)
add_dependencies(vcpkg-qt vcpkg-python)

# vcpkg-ffmpeg
get_ffmpeg_version()
set(FFMPEG_LIST_FILE ${PACKAGES_DIR}/vcpkg/installed/vcpkg/info/ffmpeg_${FFMPEG_VERSION_MAJOR}.${FFMPEG_VERSION_MINOR}.${FFMPEG_VERSION_PATCH}_${VCPKG_TRIPLET}.list)
add_custom_command(
	OUTPUT ${FFMPEG_LIST_FILE}
	COMMAND echo.
	COMMAND echo "vcpkg is building FFMpeg"
	COMMAND ${PACKAGES_DIR}/vcpkg/vcpkg.exe install ffmpeg[avcodec,avdevice,avfilter,avformat,avresample,bzip2,ffmpeg,fontconfig,freetype,lzma,opengl,swresample,swscale,x264,x265,zlib]:${VCPKG_TRIPLET} --overlay-ports=${VCPKG_OVERLAYS_DIR}
	COMMAND echo "vcpkg finished building FFMpeg"
	COMMAND echo.
)
add_custom_target(
	vcpkg-ffmpeg ALL
	DEPENDS ${FFMPEG_LIST_FILE}
)
add_dependencies(vcpkg-ffmpeg vcpkg-qt)

# vcpkg-oiio
get_oiio_version()
set(OIIO_LIST_FILE ${PACKAGES_DIR}/vcpkg/installed/vcpkg/info/openimageio_${OIIO_VERSION_MAJOR}.${OIIO_VERSION_MINOR}.${OIIO_VERSION_PATCH}.${OIIO_VERSION_TWEAK}_${VCPKG_TRIPLET}.list)
add_custom_command(
	OUTPUT ${OIIO_LIST_FILE}
	COMMAND echo.
	COMMAND echo "vcpkg is building OpenImageIO"
	COMMAND ${PACKAGES_DIR}/vcpkg/vcpkg.exe install openimageio[ffmpeg,freetype,gif,libheif,libraw,opencolorio,openjpeg,pybind11,tools,webp]:${VCPKG_TRIPLET} --overlay-ports=${VCPKG_OVERLAYS_DIR}
	COMMAND echo "vcpkg finished building OpenImageIO"
	COMMAND echo.

)
add_custom_target(
	vcpkg-oiio ALL
	DEPENDS ${OIIO_LIST_FILE}
)
add_dependencies(vcpkg-oiio vcpkg-ffmpeg)

# PySide
if(QT_VERSION_MAJOR STREQUAL 5)
    set(PYSIDE "PySide2")
	set(PYSIDE_VERSION_MAJOR "2")
    set(SHIBOKEN "shiboken2")
elseif(QT_VERSION_MAJOR STREQUAL 6)
    set(PYSIDE "PySide6")
	set(PYSIDE_VERSION_MAJOR "6")
    set(SHIBOKEN "shiboken6")
else()
    message(FATAL_ERROR "Build script only supports Qt5 or Qt6")
endif()

string(TOLOWER  ${PYSIDE} PYSIDE_LOWER)
string(TOLOWER  ${SHIBOKEN} SHIBOKEN_LOWER)

set(PYSIDE_DIR "${PACKAGES_DIR}/pyside-setup")
set(VCPKG_PYTHON_DIR "${PACKAGES_DIR}/vcpkg/installed/${VCPKG_TRIPLET}/tools/python${PYTHON_VERSION_MAJOR}")
set(VCPKG_PYTHON_INCLUDE_DIR "${PACKAGES_DIR}/vcpkg/installed/${VCPKG_TRIPLET}/include/python${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}")
set(PYTHON_DIR "${PACKAGES_DIR}/python")
set(QT_QMAKE "${PACKAGES_DIR}/vcpkg/tools/qt${QT_VERSION_MAJOR}/bin/qmake.exe")
set(LLVM_INSTALL_DIR "${PACKAGES_DIR}/libclang")

# Build bookmarks and image util
get_filename_component(
	REQUIREMENTS_FILE "../requirements.txt"
    REALPATH BASE_DIR "${CMAKE_SOURCE_DIR}"
)

configure_file(${CMAKE_SOURCE_DIR}/build-pyside.bat.in ${PACKAGES_DIR}/build-pyside.bat)
configure_file(${CMAKE_SOURCE_DIR}/build-package.bat.in ${PACKAGES_DIR}/build-package.bat)
configure_file(${CMAKE_SOURCE_DIR}/build-imageutil.bat.in ${CMAKE_BINARY_DIR}/build-imageutil.bat)

# Build bookmarks launcher
add_subdirectory(launcher)

# Installer
set(ICON_FILE "${CMAKE_SOURCE_DIR}/../bookmarks/rsc/icon.ico")
set(WIZARD_IMAGE "${CMAKE_SOURCE_DIR}/installer/WIZMODERNIMAGE.BMP")
set(WIZARD_IMAGE_SMALLE "${CMAKE_SOURCE_DIR}/installer/WIZMODERNSMALLIMAGE.BMP")
set(PACKAGE_DIR "${CMAKE_SOURCE_DIR}/build/package")
set(SOURCE_DIR "${CMAKE_SOURCE_DIR}/../bookmarks")
set(LICENSE_FILE "${CMAKE_SOURCE_DIR}/../LICENSE")
configure_file(${CMAKE_SOURCE_DIR}/installer/installer.iss.in ${CMAKE_BINARY_DIR}/install/installer.iss)
