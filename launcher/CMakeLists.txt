cmake_minimum_required(VERSION 3.16)

# set the project name
project(
	Bookmarks
	VERSION 0.7.1
	DESCRIPTION "Bookmarks and binary distribution package."
	HOMEPAGE_URL "https://github.com/wgergely/bookmarks"
)

# add the Bookmarks executable
add_executable(Bookmarks src/main.cxx src/main.rc)
configure_file("${PROJECT_SOURCE_DIR}/../bookmarks/rsc/icon.ico"
				"${PROJECT_BINARY_DIR}/icon.ico" COPYONLY)
configure_file(include/config.h.in include/config.h)
target_include_directories(
	Bookmarks PRIVATE
    "${PROJECT_BINARY_DIR}/include"
)
if(NOT CMAKE_DEBUG_POSTFIX)
  set(CMAKE_DEBUG_POSTFIX _d)
endif()
set_target_properties(Bookmarks PROPERTIES DEBUG_POSTFIX ${CMAKE_DEBUG_POSTFIX})


# Specify C++ standard
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED True)


# Find Python3
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
if (Python3_FOUND)
	message(STATUS "Found Python3")
else()
	message(STATUS "Could not find python")
endif()

set(Python3_EXECUTABLE ${Python3_EXECUTABLE} CACHE FILEPATH "Path to the Python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR} executable")
message(STATUS "Python executable: ${Python3_EXECUTABLE}")

set(Python3_INCLUDE_DIR ${Python3_INCLUDE_DIRS} CACHE PATH "Path to the Python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR} headers folder")
message(STATUS "Python include: ${Python3_INCLUDE_DIRS}")

set(Python3_LIBRARY ${Python3_LIBRARIES} CACHE FILEPATH "Path to the Python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR} release library")
message(STATUS "Python library: ${Python3_LIBRARIES}")

get_filename_component(Python3_ROOT_DIR ${Python3_EXECUTABLE} DIRECTORY)
find_file(Python3_ZIP "python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}.zip"
	PATHS  ${Python3_ROOT_DIR}
	NO_DEFAULT_PATH
)
message(STATUS "python.zip: ${Python3_ZIP}")

find_file(Python3_DLL "python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}.dll"
	PATHS  ${Python3_ROOT_DIR}
	NO_DEFAULT_PATH
)
message(STATUS "python.dll: ${Python3_DLL}")


include_directories(${Python3_INCLUDE_DIRS})
target_link_libraries(Bookmarks ${Python3_LIBRARIES})


SET(CMAKE_ARCHIVE_OUTPUT_DIRECTORY
    ${CMAKE_BINARY_DIR}/build/lib CACHE
    PATH "Directory where all the .lib files are dumped." FORCE)
SET(CMAKE_RUNTIME_OUTPUT_DIRECTORY
    ${CMAKE_BINARY_DIR}/build/bin CACHE
    PATH "Directory where .exe and .dll files are dumped." FORCE)

# FFMPEG
set(FFMPEG_EXECUTABLE CACHE FILEPATH "Path to the FFMpeg executable")
set(FFMPEG_DEPENDENCIES CACHE STRING "';' separated list of runtime libraries ffmpeg depends on")

# OPENIMAGEIO
set(OIIO_DLL CACHE FILEPATH "Path to the OpenImageIO dynamic library")
set(OIIO_PYD CACHE FILEPATH "Path to the OpenImageIO python dynamic library")
set(OIIO_DEPENDENCIES CACHE STRING "';' separated list of runtime libraries OpenImageIO depends on")

# QT5
set(QT5_CORE CACHE FILEPATH "Path to the Qt5Core dynamic library")
set(QT5_GUI CACHE FILEPATH "Path to the Qt5Gui dynamic library")
set(QT5_WIDGETS CACHE FILEPATH "Path to the Qt5Widgets dynamic library")
set(QT5_SQL CACHE FILEPATH "Path to the Qt5Sql dynamic library")
set(QT5_PLATFORM CACHE FILEPATH "Path to the Qt5 platform ynamic library (qwindows.dll)")
set(QT5_DEPENDENCIES CACHE FILEPATH "A ';' separated dynamic libraries QT5 requires to run")

# Python dependencies
set(PySide2_PySide2_DIR CACHE PATH "Path to the PySide2 python module")
set(PySide2_PySide2_DLL CACHE FILEPATH "Path to the PySide2 dynamic library")
set(PySide2_Shiboken2_DIR CACHE PATH "Path to the Shiboken2 python module")
set(PySide2_Shiboken2_DLL CACHE FILEPATH "Path to the Shiboken2 dynamic library")

# Python dependencies
set(PY_NUMPY_DIR CACHE PATH "Path to the Numpy python module")
set(PY_PSUTIL_DIR CACHE PATH "Path to the psutil python module")
set(PY_SHOTGUNAPI3_DIR CACHE PATH "Path to the shotgun_api3 python module")
set(PY_SLACK_DIR CACHE PATH "Path to the Slack_sdk python module")

# Distribution package
install(TARGETS Bookmarks
        CONFIGURATIONS Release
        RUNTIME DESTINATION .)
install(TARGETS Bookmarks
        CONFIGURATIONS Release
        RUNTIME_DEPENDENCY_SET  DESTINATION .)	
install(DIRECTORY DESTINATION ./bin)
install(DIRECTORY DESTINATION ./core)
install(DIRECTORY DESTINATION ./DLLs)
install(DIRECTORY DESTINATION ./platforms)
install(DIRECTORY DESTINATION ./shared)

# Install Python
if(EXISTS ${Python3_ZIP})
	install(FILES "${Python3_ZIP}" DESTINATION .)
endif()
if(EXISTS ${Python3_DLL})
	install(FILES "${Python3_DLL}" DESTINATION .)
endif()
if(EXISTS ${Python3_EXECUTABLE})
	install(FILES "${Python3_EXECUTABLE}" DESTINATION .)
endif()
if(EXISTS "${CMAKE_SOURCE_DIR}/../bookmarks")
	install(DIRECTORY "${CMAKE_SOURCE_DIR}/../bookmarks" DESTINATION ./shared)
endif()
if(EXISTS "${CMAKE_SOURCE_DIR}/python/.pythonstartup")
	install(FILES "${CMAKE_SOURCE_DIR}/python/.pythonstartup" DESTINATION .)
endif()
if(EXISTS "${CMAKE_SOURCE_DIR}/python/python.bat")
	install(FILES "${CMAKE_SOURCE_DIR}/python/python.bat" DESTINATION .)
endif()


if(EXISTS ${FFMPEG_EXECUTABLE})
	install(FILES "${FFMPEG_EXECUTABLE}" DESTINATION ./bin)
endif()
if(NOT "${FFMPEG_DEPENDENCIES}" STREQUAL "")
	install(FILES "${FFMPEG_DEPENDENCIES}" DESTINATION ./bin)
endif()

if(EXISTS ${OIIO_DLL})
	install(FILES "${OIIO_DLL}" DESTINATION ./bin)
endif()
if(EXISTS ${OIIO_PYD})
	install(FILES "${OIIO_PYD}" DESTINATION ./shared)
endif()
if(NOT "${OIIO_DEPENDENCIES}" STREQUAL "")
	install(FILES "${OIIO_DEPENDENCIES}" DESTINATION ./bin)
endif()

if(EXISTS ${QT5_CORE})
	install(FILES "${QT5_CORE}" DESTINATION ./core)
endif()
if(EXISTS ${QT5_GUI})
	install(FILES "${QT5_GUI}" DESTINATION ./core)
endif()
if(EXISTS ${QT5_WIDGETS})
	install(FILES "${QT5_WIDGETS}" DESTINATION ./core)
endif()
if(EXISTS ${QT5_SQL})
	install(FILES "${QT5_SQL}" DESTINATION ./core)
endif()
if(EXISTS ${QT5_PLATFORM})
	install(FILES "${QT5_PLATFORM}" DESTINATION ./platform)
endif()
if(NOT "${QT5_DEPENDENCIES}" STREQUAL "")
	install(FILES "${QT5_DEPENDENCIES}" DESTINATION ./core)
endif()

if(EXISTS ${PySide2_PySide2_DIR})
	install(DIRECTORY "${PySide2_PySide2_DIR}" DESTINATION ./core)
endif()
if(EXISTS ${PySide2_PySide2_DLL})
	install(FILES "${PySide2_PySide2_DLL}" DESTINATION ./core)
endif()
if(EXISTS ${PySide2_Shiboken2_DIR})
	install(DIRECTORY "${PySide2_Shiboken2_DIR}" DESTINATION ./core)
endif()
if(EXISTS ${PySide2_Shiboken2_DLL})
	install(FILES "${PySide2_Shiboken2_DLL}" DESTINATION ./core)
endif()

if(EXISTS ${PY_NUMPY_DIR})
	install(DIRECTORY "${PY_NUMPY_DIR}" DESTINATION ./shared)
endif()
if(EXISTS ${PY_PSUTIL_DIR})
	install(DIRECTORY "${PY_PSUTIL_DIR}" DESTINATION ./shared)
endif()
if(EXISTS ${PY_SHOTGUNAPI3_DIR})
	install(DIRECTORY "${PY_SHOTGUNAPI3_DIR}" DESTINATION ./shared)
endif()
if(EXISTS ${PY_SLACK_DIR})
	install(DIRECTORY "${PY_SLACK_DIR}" DESTINATION ./shared)
endif()