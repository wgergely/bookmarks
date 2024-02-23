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
if (NOT VCPKG_DIR OR NOT EXISTS ${VCPKG_DIR})
    message(FATAL_ERROR "[BOOKMARKS] Error: VCPKG_DIR is not set. Please set VCPKG_DIR to the vcpkg directory.")
else()
    message(STATUS "[BOOKMARKS] VCPKG_DIR: ${VCPKG_DIR}")
endif()

set(CMAKE_TOOLCHAIN_FILE "${VCPKG_DIR}/scripts/buildsystems/vcpkg.cmake" CACHE FILEPATH "Vcpkg toolchain file" FORCE)
if (NOT EXISTS ${CMAKE_TOOLCHAIN_FILE})
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


if (BUILD_PY OR BUILD_APP OR BUILD_IMAGEUTIL)
    find_package(Python COMPONENTS Interpreter Development REQUIRED)
endif()

# ===================================    
# Py
# ===================================

if (BUILD_PY)
    message(STATUS "[BOOKMARKS] [*] Building Py")

    add_executable(Python ${CMAKE_CURRENT_SOURCE_DIR}/src/python.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/env.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc)
    target_include_directories(Python PRIVATE Python::Python ${CMAKE_CURRENT_SOURCE_DIR}/include)
    target_link_libraries(Python Python::Python)
    set_target_properties(Python PROPERTIES OUTPUT_NAME "python")
    install(TARGETS Python DESTINATION bin)
    install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/src/.pythonstartup" DESTINATION bin)
else()
    message(STATUS "[BOOKMARKS] [ ] Skipping Python")
endif()

# ===================================
# App
# ===================================

if (BUILD_APP)
    message(STATUS "[BOOKMARKS] [*] Building App")
    
    # App launcher
    add_executable(App ${CMAKE_CURRENT_SOURCE_DIR}/src/app.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/env.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc)
    target_include_directories(App PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
    set_target_properties(App PROPERTIES OUTPUT_NAME "Bookmarks")
    set_property(TARGET App PROPERTY VS_SPECTRE_MITIGATION "Bookmarks.manifest")
    target_compile_definitions(App PRIVATE NO_CONSOLE=1)
    install(TARGETS App DESTINATION bin)

    # App launcher with console window
    add_executable(App-Console ${CMAKE_CURRENT_SOURCE_DIR}/src/app.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/env.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc)
    target_include_directories(App-Console PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
    set_target_properties(App-Console PROPERTIES OUTPUT_NAME "Bookmarks-console")
    set_property(TARGET App-Console PROPERTY VS_SPECTRE_MITIGATION "Bookmarks.manifest")
    install(TARGETS App-Console DESTINATION bin)

    # Python code launcher
    add_executable(Py-Launcher ${CMAKE_CURRENT_SOURCE_DIR}/src/py-launcher.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/icon.rc)
    target_include_directories(Py-Launcher PRIVATE Python::Python ${CMAKE_CURRENT_SOURCE_DIR}/include)
    target_link_libraries(Py-Launcher Python::Python)
    set_target_properties(Py-Launcher PROPERTIES OUTPUT_NAME "py-launcher")
    target_compile_definitions(Py-Launcher PRIVATE NO_CONSOLE=1)
    install(TARGETS Py-Launcher DESTINATION bin)
else()
    message(STATUS "[BOOKMARKS] [ ] Skipping App")
endif()


if (BUILD_IMAGEUTIL)
    message(STATUS "[BOOKMARKS] [*] Building imageutil")

    find_package(pybind11 REQUIRED)
    find_package(OpenImageIO CONFIG REQUIRED)
    
    # pyimageutil library
    pybind11_add_module(pyimageutil MODULE ${CMAKE_CURRENT_SOURCE_DIR}/src/pyimageutil.cpp)
    target_compile_definitions(pyimageutil PRIVATE -DBUILD_PYBIND11)

    target_include_directories(pyimageutil PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include OpenImageIO::OpenImageIO)

    target_link_libraries(pyimageutil PUBLIC OpenImageIO::OpenImageIO)
    target_link_libraries(pyimageutil PRIVATE pybind11::pybind11)

    # imageutil library
    add_library(libimageutil STATIC src/pyimageutil.cpp)

    target_include_directories(libimageutil PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include OpenImageIO::OpenImageIO)
    target_link_libraries(libimageutil PUBLIC OpenImageIO::OpenImageIO)

    # imageutil executable
    add_executable(imageutil src/imageutil.cpp)

    target_include_directories(imageutil PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include OpenImageIO::OpenImageIO)
    target_link_libraries(imageutil PRIVATE libimageutil)
    add_dependencies(imageutil libimageutil)

    # Define install
    install(TARGETS pyimageutil DESTINATION lib/site-packages)
    install(TARGETS libimageutil DESTINATION lib)
    install(TARGETS imageutil DESTINATION bin)
else()
    message(STATUS "[BOOKMARKS] [ ] Skipping imageutil")
endif()