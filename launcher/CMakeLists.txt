cmake_minimum_required(VERSION 3.10)

# set the project name
project(
	Bookmarks
	VERSION 0.5.0
	DESCRIPTION "Bookmarks executable."
	HOMEPAGE_URL "https://github.com/wgergely/bookmarks"
)

# Get the source from github


# add the executable
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



# specify the C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)


# Find Python
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
include_directories(${Python3_INCLUDE_DIRS})
link_directories(${Python3_LIBRARY_DIRS})

set(Python3_EXECUTABLE ${Python3_EXECUTABLE} CACHE FILEPATH "" FORCE)
set(Python3_INCLUDE_DIRS ${Python3_INCLUDE_DIRS} CACHE PATH "" FORCE)
set(Python3_LIBRARIES ${Python3_LIBRARIES} CACHE FILEPATH "" FORCE)
message(STATUS "Found ${Python3_EXECUTABLE}")
message(STATUS "Found ${Python3_INCLUDE_DIRS}")
message(STATUS "Found ${Python3_LIBRARIES}")


SET(CMAKE_ARCHIVE_OUTPUT_DIRECTORY
    ${CMAKE_BINARY_DIR}/build/lib CACHE
    PATH "Directory where all the .lib files are dumped." FORCE)
SET(CMAKE_RUNTIME_OUTPUT_DIRECTORY
    ${CMAKE_BINARY_DIR}/build/bin CACHE
    PATH "Directory where .exe and .dll files are dumped." FORCE)


# INSTALL REQUIRED PACKAGE
set(Package_PythonZIP CACHE FILEPATH "Path to the Python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}.zip file")
get_filename_component(Package_PythonZIPName "${Package_PythonZIP}" NAME)

set(Package_FFMpegBIN CACHE FILEPATH "Path to the FFMpeg executable")
get_filename_component(Package_FFMpegBINName "${Package_FFMpegBIN}" NAME)
	
get_filename_component(Python3_EXECUTABLEName "${Python3_EXECUTABLE}" NAME)


install(TARGETS Bookmarks
        CONFIGURATIONS Release
        RUNTIME DESTINATION .)
install(TARGETS Bookmarks
        CONFIGURATIONS Release
        RUNTIME_DEPENDENCY_SET  DESTINATION .)		
install(DIRECTORY DESTINATION ./core)
install(DIRECTORY DESTINATION ./shared)
install(DIRECTORY DESTINATION ./bin)
install(DIRECTORY DESTINATION ./platforms)

if(NOT EXISTS ${Package_PythonZIP})
	message(WARNING "Python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}.zip not found")
else()
	install(FILES "${Package_PythonZIP}" DESTINATION .)
endif()

if(NOT EXISTS ${Package_FFMpegBIN})
	message(WARNING "FFMpeg executable not found")
else()
	install(FILES "${Package_FFMpegBIN}" DESTINATION ./bin)
endif()

if(NOT EXISTS ${Python3_EXECUTABLE})
	message(WARNING "Python executable not found")
else()
	install(FILES "${Python3_EXECUTABLE}" DESTINATION .)
endif()

message(STATUS ${CMAKE_BINARY_DIR})

install(DIRECTORY "${CMAKE_SOURCE_DIR}/../bookmarks"
		DESTINATION ./shared)