cmake_minimum_required(VERSION 3.9)
project(oiioutil LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 14)
# =====================================================================
# Find packages
find_package(pybind11 REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Development)
find_package(OpenImageIO REQUIRED)
# =====================================================================
pybind11_add_module(bookmarks_oiio MODULE src/oiioutil.cpp)
target_include_directories(bookmarks_oiio PRIVATE ${OpenImageIO_INCLUDE_DIR})
target_link_libraries(bookmarks_oiio PUBLIC ${OpenImageIO_LIB_DIR}/OpenImageIO.lib)
target_link_libraries(bookmarks_oiio PUBLIC ${OpenImageIO_LIB_DIR}/OpenImageIO_Util.lib)
target_link_libraries(bookmarks_oiio PRIVATE pybind11::pybind11)
# =====================================================================
# Install
install(
    TARGETS bookmarks_oiio
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib/site-packages
    ARCHIVE DESTINATION static
)