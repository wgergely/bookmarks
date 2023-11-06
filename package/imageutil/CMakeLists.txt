cmake_minimum_required(VERSION 3.20)
set(CMAKE_CXX_STANDARD 14)

project(
	imageutil
	VERSION 0.1.0
	DESCRIPTION "Utility library for the Bookmarks python module"
	HOMEPAGE_URL "https://bookmarks-vfx.com"
)

option(BUILD_TESTS "Build the project tests" OFF)

# Find packages
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)
find_package(OpenImageIO CONFIG REQUIRED)

message(STATUS "OpenImageIO_INCLUDE_DIR: ${OpenImageIO_INCLUDE_DIR}")

# Headers and source
set(SRC_DIR ${CMAKE_SOURCE_DIR}/src)
set(INCLUDE_DIR ${CMAKE_SOURCE_DIR}/include)

# pyimageutil
pybind11_add_module(pyimageutil MODULE ${SRC_DIR}/pyimageutil.cpp)
set_target_properties(pyimageutil PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/build
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/build
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/build
)


# Set the platform details
if(WIN32)
    set(PLATFORM_TAG "win_amd64")
elseif(APPLE)
    set(PLATFORM_TAG "macosx")
else()
    set(PLATFORM_TAG "linux_x86_64")
endif()

# Get the Python version
string(REGEX MATCH "([0-9]+)\\.([0-9]+)" _  ${Python3_VERSION})
if(WIN32)
	set_target_properties(pyimageutil PROPERTIES SUFFIX ".cp${CMAKE_MATCH_1}${CMAKE_MATCH_2}-${PLATFORM_TAG}.pyd")
else()
	set_target_properties(pyimageutil PROPERTIES SUFFIX ".cp${CMAKE_MATCH_1}${CMAKE_MATCH_2}-${PLATFORM_TAG}.so")
endif()


target_compile_definitions(pyimageutil PRIVATE -DBUILD_PYBIND11)

target_include_directories(pyimageutil PRIVATE ${INCLUDE_DIR} ${OpenImageIO_INCLUDE_DIR})
target_link_libraries(pyimageutil PUBLIC OpenImageIO::OpenImageIO)
target_link_libraries(pyimageutil PRIVATE pybind11::pybind11)

# libimageutil
add_library(libimageutil STATIC ${SRC_DIR}/pyimageutil.cpp)

target_include_directories(libimageutil PRIVATE ${INCLUDE_DIR} ${OpenImageIO_INCLUDE_DIR})
target_link_libraries(libimageutil PUBLIC OpenImageIO::OpenImageIO)

# imageutil executable
add_executable(imageutil src/imageutil.cpp)
target_include_directories(imageutil PRIVATE ${INCLUDE_DIR} ${OpenImageIO_INCLUDE_DIR})
target_link_libraries(imageutil PRIVATE libimageutil)
add_dependencies(imageutil libimageutil)


# Testing
if(BUILD_TESTS)

	set(TEST_DIR ${CMAKE_BINARY_DIR}/test)
	set(OIIO_TEST_IMAGES_URL "https://github.com/OpenImageIO/oiio-images/archive/aae37a54e31c0e719edcec852994d052ecf6541e.zip")
	set(OIIO_TEST_IMAGES_DIR ${TEST_DIR}/oiio-images)
	set(OIIO_TEST_IMAGES_ZIP "${CMAKE_BINARY_DIR}/test/oiio-images.zip")
	set(OIIO_TEST_IMAGES_EXTRACTED ${TEST_DIR}/oiio-images/oiio-images-aae37a54e31c0e719edcec852994d052ecf6541e)

	configure_file(${CMAKE_SOURCE_DIR}/test/images.txt ${TEST_DIR}/images.txt COPYONLY)
	configure_file(${CMAKE_SOURCE_DIR}/test/test_oiio_images.py.in ${TEST_DIR}/test_oiio_images.py @ONLY)

	message(STATUS "Downloading oiio-images...")
	file(DOWNLOAD ${OIIO_TEST_IMAGES_URL} ${OIIO_TEST_IMAGES_ZIP}
		EXPECTED_HASH SHA512=0272ecef88ce859edead6e5a823aebe46d27542d67f827348c9c4d0576e500e82d23786bfd125bdf1dd878d5d065a2a29f23a82a8ba1053cc805c05a201f9c87
	SHOW_PROGRESS)

	file(ARCHIVE_EXTRACT INPUT ${OIIO_TEST_IMAGES_ZIP}
		DESTINATION ${OIIO_TEST_IMAGES_DIR})

	# Custom command to run Python tests
	add_custom_command(
		TARGET pyimageutil POST_BUILD  # replace 'your_target' with your actual target
		COMMAND ${Python3_EXECUTABLE} ${CMAKE_BINARY_DIR}/test/test_oiio_images.py --module $<TARGET_FILE_DIR:pyimageutil>
		COMMENT "Running Python tests..."
	)

endif()