set(CMAKE_INSTALL_PREFIX "${PROJECT_BINARY_DIR}/install")
file(MAKE_DIRECTORY ${CMAKE_INSTALL_PREFIX})
set(PACKAGE_DOWNLOAD_DIR "${PROJECT_BINARY_DIR}/download")
file(MAKE_DIRECTORY ${PACKAGE_DOWNLOAD_DIR})
set(PACKAGES_DIR "${PROJECT_BINARY_DIR}/packages")
file(MAKE_DIRECTORY ${PACKAGES_DIR})
set(PACKAGE_DIR "${PROJECT_BINARY_DIR}/package")
file(MAKE_DIRECTORY ${PACKAGE_DIR})

set(LIBCLANG_URL "https://download.qt.io/development_releases/prebuilt/libclang/libclang-release_14.0.3-based-windows-vs2019_64.7z" CACHE STRING "" FORCE)
set(LIBCLANG_SHA512 "ca45a1b827c296a6dd854d5ce22e9e4e234e6b02cbba5c97c9ccbe1ebabb99dab2c0fb2588cf3511a5ae77fe1a4e52a03b5b091a5945366bdf37a5d8abcfface" CACHE STRING "" FORCE)
get_filename_component(LIBCLANG_ARCHIVE ${LIBCLANG_URL} NAME)

set(PYTHON_EMBED_URL "https://www.python.org/ftp/python/3.9.13/python-3.9.13-embed-amd64.zip" CACHE STRING "" FORCE)
set(PYTHON_EMBED_SHA512 "0b58b0877e61738261f442d62fb9157abead571014b2f24988df5546beeffcca4b4e83eb15304556fc4306618a9b14cd6e59eab1c2bed7fb174707c8341be863" CACHE STRING "" FORCE)
get_filename_component(PYTHON_EMBED_ARCHIVE ${PYTHON_EMBED_URL} NAME)

set(INNO_URL "https://files.jrsoftware.org/is/6/innosetup-6.2.2.exe" CACHE STRING "" FORCE)
set(INNO_SHA512 "496375b1ce9c0d2f8eb3930ebd8366f5c4c938bc1eda47aed415e3f02bd8651a84a770a15f2825bf3c8ed9dbefa355b9eb805dd76bc782f6d8c8096d80443099" CACHE STRING "" FORCE)
get_filename_component(INNO_ARCHIVE ${INNO_URL} NAME)

set(VCPKG_COMMIT "a548ef5")
set(VCPKG_URL "https://github.com/microsoft/vcpkg/archive/${VCPKG_COMMIT}.tar.gz" CACHE STRING "" FORCE)
set(VCPKG_SHA256 "a548ef52e5b6b4b92de09fd0efdeaa95c745e2a0")
set(VCPKG_SHA512 "2a1b3293b13e925a677f1880d0f2f3da642917eaa1cadb2234d3d277cfac07f1215e87ee7726206c9d9c7eb27889edd2801ed793bfe14108052f1597d4a9f3f0" CACHE STRING "" FORCE)
get_filename_component(VCPKG_ARCHIVE ${VCPKG_URL} NAME)
set(VCPKG_OVERLAYS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/vcpkg_ports")
set(VCPKG_TOOLCHAIN "${PACKAGES_DIR}/vcpkg/scripts/buildsystems/vcpkg.cmake")

if (CMAKE_GENERATOR_PLATFORM STREQUAL "x64")
    set(VCPKG_TRIPLET "x64-windows")
elseif(CMAKE_GENERATOR_PLATFORM STREQUAL "Win32")
    set(VCPKG_TRIPLET "x86-windows")
else()
    message(FATAL_ERROR "Unrecognised platform: ${CMAKE_GENERATOR_PLATFORM}")
endif()


function(get_archives)
    message(STATUS "Downloading ${LIBCLANG_ARCHIVE}...")
    file(DOWNLOAD ${LIBCLANG_URL} ${PACKAGE_DOWNLOAD_DIR}/${LIBCLANG_ARCHIVE}
        EXPECTED_HASH SHA512=${LIBCLANG_SHA512}
        SHOW_PROGRESS)

    if(NOT EXISTS ${PACKAGES_DIR})
        message(STATUS "Extracting ${LIBCLANG_ARCHIVE}...")
        file(ARCHIVE_EXTRACT INPUT ${PACKAGE_DOWNLOAD_DIR}/${LIBCLANG_ARCHIVE}
            DESTINATION ${PACKAGES_DIR})
    else()
        message(STATUS "Skipping extraction of ${LIBCLANG_ARCHIVE} as it already exists.")
    endif()

    message(STATUS "Downloading ${PYTHON_EMBED_ARCHIVE}...")
    file(DOWNLOAD ${PYTHON_EMBED_URL} ${PACKAGE_DOWNLOAD_DIR}/${PYTHON_EMBED_ARCHIVE}
        EXPECTED_HASH SHA512=${PYTHON_EMBED_SHA512}
        SHOW_PROGRESS)

    if(NOT EXISTS ${PACKAGES_DIR}/python-embed)
        message(STATUS "Extracting ${PYTHON_EMBED_ARCHIVE}...")
        file(ARCHIVE_EXTRACT INPUT ${PACKAGE_DOWNLOAD_DIR}/${PYTHON_EMBED_ARCHIVE}
            DESTINATION ${PACKAGES_DIR}/python-embed)
    else()
        message(STATUS "Skipping extraction of ${PYTHON_EMBED_ARCHIVE} as it already exists.")
    endif()

    message(STATUS "Downloading ${VCPKG_ARCHIVE}...")
    file(DOWNLOAD ${VCPKG_URL} ${PACKAGE_DOWNLOAD_DIR}/${VCPKG_ARCHIVE}
        EXPECTED_HASH SHA512=${VCPKG_SHA512}
        SHOW_PROGRESS)

    if(NOT EXISTS ${PACKAGES_DIR}/vcpkg)
        message(STATUS "Extracting ${VCPKG_ARCHIVE}...")
        file(ARCHIVE_EXTRACT INPUT ${PACKAGE_DOWNLOAD_DIR}/${VCPKG_ARCHIVE}
            DESTINATION ${PACKAGES_DIR}/vcpkg)
        file(GLOB CONTENTS "${PACKAGES_DIR}/vcpkg/vcpkg-${VCPKG_SHA256}/*")
        file(COPY ${CONTENTS} DESTINATION "${PACKAGES_DIR}/vcpkg")
        file(REMOVE_RECURSE ${PACKAGES_DIR}/vcpkg/vcpkg-${VCPKG_SHA256})
    else()
        message(STATUS "Skipping extraction of ${VCPKG_ARCHIVE} as it already exists.")
    endif()

    message(STATUS "Downloading ${INNO_ARCHIVE}...")
    file(DOWNLOAD ${INNO_URL} ${PACKAGE_DOWNLOAD_DIR}/${INNO_ARCHIVE}
        EXPECTED_HASH SHA512=${INNO_SHA512}
        SHOW_PROGRESS)

    if(NOT EXISTS ${PACKAGES_DIR}/inno)
        message(STATUS "Extracting ${INNO_ARCHIVE}...")
        execute_process(
            COMMAND "${PACKAGE_DOWNLOAD_DIR}/${INNO_ARCHIVE}" "/VERYSILENT" "/DIR=${PACKAGES_DIR}/inno"
            WORKING_DIRECTORY "${PACKAGE_DOWNLOAD_DIR}"
            RESULT_VARIABLE INNO_RESULT
            OUTPUT_VARIABLE INNO_OUTPUT
        )
    else()
        message(STATUS "Skipping extraction of ${INNO_ARCHIVE} as it already exists.")
    endif()

endfunction()