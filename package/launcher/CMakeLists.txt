# Standard Bookmarks.exe application
add_executable(launcher src/bookmarks.cxx src/bookmarks.rc)
add_dependencies(launcher vcpkg-oiio)
target_include_directories(launcher PRIVATE
	"${CMAKE_CURRENT_BINARY_DIR}/include"
	"${PACKAGES_DIR}/vcpkg/installed/${VCPKG_TRIPLET}/include/python${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}"
)
target_compile_definitions(launcher PRIVATE NO_CONSOLE=1)
set_target_properties(launcher PROPERTIES OUTPUT_NAME "Bookmarks")
target_link_libraries(launcher "${PACKAGES_DIR}/vcpkg/installed/${VCPKG_TRIPLET}/lib/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}.lib")
set_property(TARGET launcher PROPERTY VS_SPECTRE_MITIGATION "Bookmarks.manifest")


# Bookmarks.exe with console window
add_executable(launcher-debug src/bookmarks.cxx src/bookmarks.rc)
add_dependencies(launcher-debug vcpkg-oiio)
target_include_directories(launcher-debug PRIVATE
	"${CMAKE_CURRENT_BINARY_DIR}/include"
	"${PACKAGES_DIR}/vcpkg/installed/${VCPKG_TRIPLET}/include/python${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}"
)
set_target_properties(launcher-debug PROPERTIES OUTPUT_NAME "Bookmarks-debug")
target_link_libraries(launcher-debug "${PACKAGES_DIR}/vcpkg/installed/${VCPKG_TRIPLET}/lib/python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}.lib")

# Copy the icon file to the build directory
configure_file(
	"${CMAKE_SOURCE_DIR}/../bookmarks/rsc/icon.ico"
	"${CMAKE_CURRENT_BINARY_DIR}/icon.ico" COPYONLY
)
configure_file(
	"${CMAKE_CURRENT_SOURCE_DIR}/include/config.h.in"
	"${CMAKE_CURRENT_BINARY_DIR}/include/config.h"
)