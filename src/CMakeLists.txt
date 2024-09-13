cmake_minimum_required(VERSION 3.18)
cmake_policy(VERSION 3.18)

# Specify C++ standard globally, if all subprojects use the same standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

set(CMAKE_BUILD_TYPE Release)

# Add cache for library version
set(Bookmarks_VERSION "0.0.0" CACHE STRING "Bookmarks version")

add_definitions(-DUNICODE -D_UNICODE -DBookmarks_VERSION="${Bookmarks_VERSION}")
message(STATUS "[BOOKMARKS] Bookmarks version: ${Bookmarks_VERSION}")

# Add switches BUILD_PY and BUILD_APP
option(BUILD_PY "Build Python bindings" ON)
option(BUILD_APP "Build app" ON)
option(BUILD_IMAGEUTIL "Build imageutil" ON)

# Copy the icon file to the build directory
configure_file(
    "${CMAKE_SOURCE_DIR}/../bookmarks/rsc/icon.ico"
    "${CMAKE_CURRENT_BINARY_DIR}/icon.ico" COPYONLY
)

# ===================================
# Vcpkg
# ===================================
set(VCPKG_DIR "" CACHE PATH "Vcpkg directory")
if (NOT VCPKG_DIR OR NOT EXISTS "${VCPKG_DIR}")
    message(FATAL_ERROR "[BOOKMARKS] Error: VCPKG_DIR is not set. Please set VCPKG_DIR to the vcpkg directory.")
else()
    message(STATUS "[BOOKMARKS] VCPKG_DIR: ${VCPKG_DIR}")
endif()

set(CMAKE_TOOLCHAIN_FILE "${VCPKG_DIR}/scripts/buildsystems/vcpkg.cmake" CACHE FILEPATH "Vcpkg toolchain file" FORCE)
if (NOT EXISTS "${CMAKE_TOOLCHAIN_FILE}")
    message(FATAL_ERROR "[BOOKMARKS] Error: CMAKE_TOOLCHAIN_FILE does not exist")
else()
    message(STATUS "[BOOKMARKS] CMAKE_TOOLCHAIN_FILE: ${CMAKE_TOOLCHAIN_FILE}")
endif()

set(VCPKG_TARGET_TRIPLET "x64-windows" CACHE STRING "Vcpkg target triplet" FORCE)
message(STATUS "[BOOKMARKS] VCPKG_TARGET_TRIPLET: ${VCPKG_TARGET_TRIPLET}")

set(VCPKG_MANIFEST_MODE "ON" CACHE STRING "Vcpkg manifest mode" FORCE)
set(VCPKG_MANIFEST_DIR "${VCPKG_DIR}" CACHE STRING "Vcpkg manifest directory" FORCE)
set(VCPKG_INSTALLED_DIR "${VCPKG_DIR}/vcpkg_installed" CACHE STRING "Vcpkg installed directory" FORCE)
set(VCPKG_MANIFEST_INSTALL "OFF" CACHE STRING "Vcpkg manifest install" FORCE)


project(Bookmarks)


find_package(Python COMPONENTS Interpreter Development REQUIRED)

# ===================================    
# Py
# ===================================

if (BUILD_PY)
    message(STATUS "[BOOKMARKS] [*] Building Py")

    # Python interpreter without the core module
    add_executable(Python "${CMAKE_CURRENT_SOURCE_DIR}/src/python.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/env.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc")
    target_compile_options(Python PRIVATE /utf-8)
    target_include_directories(Python PRIVATE Python::Python "${CMAKE_CURRENT_SOURCE_DIR}/include")
    target_link_libraries(Python Python::Python)
    set_target_properties(Python PROPERTIES OUTPUT_NAME "python")
    install(TARGETS Python DESTINATION bin)

    # Python interpreter with the core module
    add_executable(Python-M "${CMAKE_CURRENT_SOURCE_DIR}/src/python.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/env.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc")
    target_compile_options(Python-M PRIVATE /utf-8)
    target_include_directories(Python-M PRIVATE Python::Python "${CMAKE_CURRENT_SOURCE_DIR}/include")
    target_link_libraries(Python-M Python::Python)
    set_target_properties(Python-M PROPERTIES OUTPUT_NAME "python-with-core")
    target_compile_definitions(Python-M PRIVATE ADD_CORE_MODULE=1)
    install(TARGETS Python-M DESTINATION bin)
else()
    message(STATUS "[BOOKMARKS] [ ] Skipping Python")
endif()

# ===================================
# App
# ===================================

if (BUILD_APP)
    message(STATUS "[BOOKMARKS] [*] Building App")

    # App launcher
    add_executable(App "${CMAKE_CURRENT_SOURCE_DIR}/src/app.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/env.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc")
    target_compile_options(App PRIVATE /utf-8)
    target_include_directories(App PRIVATE Python::Python "${CMAKE_CURRENT_SOURCE_DIR}/include")
    set_target_properties(App PROPERTIES OUTPUT_NAME "Bookmarks")

    set_property(TARGET App PROPERTY VS_SPECTRE_MITIGATION "Bookmarks.manifest")
    target_compile_definitions(App PRIVATE NO_CONSOLE=1)
    install(TARGETS App DESTINATION bin)

    # App launcher with console window
    add_executable(App-Console "${CMAKE_CURRENT_SOURCE_DIR}/src/app.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/env.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc")
    target_compile_options(App-Console PRIVATE /utf-8)
    target_include_directories(App-Console PRIVATE Python::Python "${CMAKE_CURRENT_SOURCE_DIR}/include")
    set_target_properties(App-Console PROPERTIES OUTPUT_NAME "Bookmarks-console")
    set_property(TARGET App-Console PROPERTY VS_SPECTRE_MITIGATION "Bookmarks.manifest")
    install(TARGETS App-Console DESTINATION bin)

    # Python code launcher
    add_executable(Py-Launcher "${CMAKE_CURRENT_SOURCE_DIR}/src/py-launcher.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/env.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc")
    target_compile_options(Py-Launcher PRIVATE /utf-8)
    target_include_directories(Py-Launcher PRIVATE Python::Python "${CMAKE_CURRENT_SOURCE_DIR}/include")
    target_link_libraries(Py-Launcher Python::Python)
    set_target_properties(Py-Launcher PROPERTIES OUTPUT_NAME "launch")
    target_compile_definitions(Py-Launcher PRIVATE NO_CONSOLE=1)
    install(TARGETS Py-Launcher DESTINATION bin)
else()
    message(STATUS "[BOOKMARKS] [ ] Skipping App")
endif()


if (BUILD_IMAGEUTIL)
    message(STATUS "[BOOKMARKS] [*] Building imageutil")

    find_package(pybind11 REQUIRED)
    find_package(OpenImageIO CONFIG REQUIRED)

    # imageutil executable
    add_executable(ImageUtil "${CMAKE_CURRENT_SOURCE_DIR}/src/imageutil.cpp")
    target_compile_options(ImageUtil PRIVATE /utf-8)
    target_include_directories(ImageUtil PRIVATE Python::Python "${CMAKE_CURRENT_SOURCE_DIR}/include" OpenImageIO::OpenImageIO)
    target_link_libraries(ImageUtil PUBLIC OpenImageIO::OpenImageIO)
    set_target_properties(ImageUtil PROPERTIES OUTPUT_NAME "bookmarks_openimageio")
    install(TARGETS ImageUtil DESTINATION bin)

    # imageutil python module
    pybind11_add_module(Py-ImageUtil MODULE "${CMAKE_CURRENT_SOURCE_DIR}/src/imageutil.cpp")
    target_compile_options(Py-ImageUtil PRIVATE /utf-8)
    target_include_directories(Py-ImageUtil PRIVATE Python::Python "${CMAKE_CURRENT_SOURCE_DIR}/include" OpenImageIO::OpenImageIO)
    target_link_libraries(Py-ImageUtil PUBLIC OpenImageIO::OpenImageIO)
    target_link_libraries(Py-ImageUtil PRIVATE pybind11::pybind11)
    set_target_properties(Py-ImageUtil PROPERTIES OUTPUT_NAME "bookmarks_openimageio")
    target_compile_definitions(Py-ImageUtil PRIVATE _PYBIND_MODULE=bookmarks_openimageio)
    install(TARGETS Py-ImageUtil DESTINATION lib/site-packages)
else()
    message(STATUS "[BOOKMARKS] [ ] Skipping imageutil")
endif()