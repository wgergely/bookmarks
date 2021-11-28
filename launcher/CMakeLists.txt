cmake_minimum_required(VERSION 3.10)

# set the project name
project(
	Bookmarks
	VERSION 0.5.0
	DESCRIPTION "Bookmarks executable."
	HOMEPAGE_URL "https://github.com/wgergely/bookmarks"
)

# add the executable
add_executable(Bookmarks src/main.cxx src/main.rc)
configure_file("${PROJECT_SOURCE_DIR}/../bookmarks/rsc/icon.ico" "${PROJECT_BINARY_DIR}/icon.ico" COPYONLY)

configure_file(include/config.h.in include/config.h)
target_include_directories(
	Bookmarks PRIVATE
    "${PROJECT_BINARY_DIR}/include"
)

# specify the C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_INSTALL_PREFIX "${PROJECT_BIN_DIR}")

# Find Python
find_package(Python3 COMPONENTS Development REQUIRED)
include_directories(${Python3_INCLUDE_DIRS})
link_directories(${Python3_LIBRARY_DIRS})
message("Python3_INCLUDE_DIRS: ${Python3_INCLUDE_DIRS}")
message("Python3_LIBRARY_DIRS: ${Python3_LIBRARY_DIRS}")

install(TARGETS Bookmarks
        CONFIGURATIONS Debug
        RUNTIME DESTINATION Debug/bin)
install(TARGETS Bookmarks
        CONFIGURATIONS Release
        RUNTIME DESTINATION Release/bin)