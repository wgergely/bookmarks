cmake_minimum_required(VERSION 3.9)

project(oiioutil)
set(CMAKE_CXX_STANDARD 14)

find_package("OpenImageIO" REQUIRED)

# Add the include directories to the include paths
include_directories(${OpenImageIO_INCLUDE_DIRS})

# Link directories
link_directories(${OpenImageIO_LIBRARY_DIRS})

# Set up the C++ source files
add_library(bookmarks_oiio SHARED src/oiioutil.cpp)

target_include_directories(bookmarks_oiio PRIVATE ${OpenImageIO_INCLUDE_DIR})
target_link_libraries(bookmarks_oiio PUBLIC ${OpenImageIO_LIB_DIR}/OpenImageIO.lib)
target_link_libraries(bookmarks_oiio PUBLIC ${OpenImageIO_LIB_DIR}/OpenImageIO_Util.lib)

# Set up the C++ source files
add_executable(bookmarks_oiio_bin src/oiioutil.cpp)

target_include_directories(bookmarks_oiio_bin PRIVATE ${OpenImageIO_INCLUDE_DIR})
target_link_libraries(bookmarks_oiio_bin PUBLIC ${OpenImageIO_LIB_DIR}/OpenImageIO.lib)
target_link_libraries(bookmarks_oiio_bin PUBLIC ${OpenImageIO_LIB_DIR}/OpenImageIO_Util.lib)


# Install
set(CMAKE_INSTALL_PREFIX "${CMAKE_CURRENT_SOURCE_DIR}/lib" CACHE PATH "Cmake prefix" FORCE)
install(TARGETS bookmarks_oiio DESTINATION .)
install(TARGETS bookmarks_oiio_bin DESTINATION .)