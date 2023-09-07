function(get_portfile_path package_name portfile_name output_var)
    set(overlay_path "${VCPKG_OVERLAYS_DIR}/${package_name}/${portfile_name}")
    set(original_path "${PACKAGES_DIR}/vcpkg/ports/${package_name}/${portfile_name}")

    if(EXISTS ${overlay_path})
        set(${output_var} ${overlay_path} PARENT_SCOPE)
    elseif(EXISTS ${original_path})
        set(${output_var} ${original_path} PARENT_SCOPE)
    else()
        message(FATAL_ERROR "Portfile for ${package_name} not found in either overlay or original vcpkg ports directory!")
    endif()
endfunction()


function(get_qt_version)
    get_portfile_path(qt5-base vcpkg.json QT_PORTFILE_PATH)
    file(READ ${QT_PORTFILE_PATH} _QT_PORTFILE_CONTENTS)

    set(QT_SEMVER_REGEX " *\"version.*\": \"([0-9]+)\\.([0-9]+)\\.([0-9]+)\" *")
    string(REGEX MATCH ${QT_SEMVER_REGEX} QT_VERSIONS ${_QT_PORTFILE_CONTENTS})
    string(REGEX REPLACE ${QT_SEMVER_REGEX} "\\1" QT_VERSION_MAJOR ${QT_VERSIONS})
    string(REGEX REPLACE ${QT_SEMVER_REGEX} "\\2" QT_VERSION_MINOR ${QT_VERSIONS})
    string(REGEX REPLACE ${QT_SEMVER_REGEX} "\\3" QT_VERSION_PATCH ${QT_VERSIONS})

    set(QT_VERSION_MAJOR ${QT_VERSION_MAJOR} CACHE STRING "" FORCE)
    set(QT_VERSION_MINOR ${QT_VERSION_MINOR} CACHE STRING "" FORCE)
    set(QT_VERSION_PATCH ${QT_VERSION_PATCH} CACHE STRING "" FORCE)

    # Check if regex match was successful
    if("${QT_VERSION_MAJOR}" STREQUAL "" OR "${QT_VERSION_MINOR}" STREQUAL "" OR "${QT_VERSION_PATCH}" STREQUAL "")
        message(FATAL_ERROR "Failed to extract Qt version from portfile.")
    endif()

    if(${QT_PORTFILE_PATH} STREQUAL "${VCPKG_OVERLAYS_DIR}/qt5-base/vcpkg.json")
        message(STATUS "Qt version: ${QT_VERSION_MAJOR}.${QT_VERSION_MINOR}.${QT_VERSION_PATCH} (from overlay port file)")
    else()
        message(STATUS "Qt version: ${QT_VERSION_MAJOR}.${QT_VERSION_MINOR}.${QT_VERSION_PATCH} (from original port file)")
    endif()

endfunction()


function(get_python_version)
    get_portfile_path(python3 portfile.cmake PYTHON_PORTFILE_PATH)
    file(READ ${PYTHON_PORTFILE_PATH} _PYTHON_PORTFILE_CONTENTS)
    
    string(REGEX MATCH "set *\\(PYTHON_VERSION_MAJOR *([0-9]+)\\)" PYTHON_VERSION_MAJOR ${_PYTHON_PORTFILE_CONTENTS})
    string(REGEX REPLACE "set *\\(PYTHON_VERSION_MAJOR *([0-9]+)\\)" "\\1" PYTHON_VERSION_MAJOR ${PYTHON_VERSION_MAJOR})

    string(REGEX MATCH "set *\\(PYTHON_VERSION_MINOR *([0-9]+)\\)" PYTHON_VERSION_MINOR ${_PYTHON_PORTFILE_CONTENTS})
    string(REGEX REPLACE "set *\\(PYTHON_VERSION_MINOR *([0-9]+)\\)" "\\1" PYTHON_VERSION_MINOR ${PYTHON_VERSION_MINOR})

    string(REGEX MATCH "set *\\(PYTHON_VERSION_PATCH *([0-9]+)\\)" PYTHON_VERSION_PATCH ${_PYTHON_PORTFILE_CONTENTS})
    string(REGEX REPLACE "set *\\(PYTHON_VERSION_PATCH *([0-9]+)\\)" "\\1" PYTHON_VERSION_PATCH ${PYTHON_VERSION_PATCH})

    set(PYTHON_VERSION_MAJOR ${PYTHON_VERSION_MAJOR} CACHE STRING "" FORCE)
    set(PYTHON_VERSION_MINOR ${PYTHON_VERSION_MINOR} CACHE STRING "" FORCE)
    set(PYTHON_VERSION_PATCH ${PYTHON_VERSION_PATCH} CACHE STRING "" FORCE)

    # Check if regex match was successful
    if("${PYTHON_VERSION_MAJOR}" STREQUAL "" OR "${PYTHON_VERSION_MINOR}" STREQUAL "" OR "${PYTHON_VERSION_PATCH}" STREQUAL "")
        message(FATAL_ERROR "Failed to extract Python version from portfile.")
    endif()

    if(${PYTHON_PORTFILE_PATH} STREQUAL "${VCPKG_OVERLAYS_DIR}/python3/portfile.cmake")
        message(STATUS "Python version: ${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}.${PYTHON_VERSION_PATCH} (from overlay port file)")
    else()
        message(STATUS "Python version: ${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}.${PYTHON_VERSION_PATCH} (from original port file)")
    endif()

endfunction()


function(get_ffmpeg_version)
    get_portfile_path(ffmpeg vcpkg.json FFMPEG_PORTFILE_PATH)
    file(READ ${FFMPEG_PORTFILE_PATH} _FFMPEG_PORTFILE_CONTENTS)

    set(FFMPEG_SEMVER_REGEX ".*\"version.*\": \"([0-9]+)\.([0-9]+)\.([0-9]+)\".*")
    string(REGEX MATCH ${FFMPEG_SEMVER_REGEX} FFMPEG_VERSIONS ${_FFMPEG_PORTFILE_CONTENTS})
    string(REGEX REPLACE ${FFMPEG_SEMVER_REGEX} "\\1" FFMPEG_VERSION_MAJOR ${FFMPEG_VERSIONS})
    string(REGEX REPLACE ${FFMPEG_SEMVER_REGEX} "\\2" FFMPEG_VERSION_MINOR ${FFMPEG_VERSIONS})
    string(REGEX REPLACE ${FFMPEG_SEMVER_REGEX} "\\3" FFMPEG_VERSION_PATCH ${FFMPEG_VERSIONS})

    set(FFMPEG_VERSION_MAJOR ${FFMPEG_VERSION_MAJOR} CACHE STRING "" FORCE)
    set(FFMPEG_VERSION_MINOR ${FFMPEG_VERSION_MINOR} CACHE STRING "" FORCE)
    set(FFMPEG_VERSION_PATCH ${FFMPEG_VERSION_PATCH} CACHE STRING "" FORCE)

    # Check if regex match was successful
    if("${FFMPEG_VERSION_MAJOR}" STREQUAL "" OR "${FFMPEG_VERSION_MINOR}" STREQUAL "" OR "${FFMPEG_VERSION_PATCH}" STREQUAL "")
        message(FATAL_ERROR "Failed to extract FFMpeg version from portfile.")
    endif()

    if(${FFMPEG_PORTFILE_PATH} STREQUAL "${VCPKG_OVERLAYS_DIR}/ffmpeg/vcpkg.json")
        message(STATUS "FFMpeg version: ${FFMPEG_VERSION_MAJOR}.${FFMPEG_VERSION_MINOR}.${FFMPEG_VERSION_PATCH} (from overlay port file)")
    else()
        message(STATUS "FFMpeg version: ${FFMPEG_VERSION_MAJOR}.${FFMPEG_VERSION_MINOR}.${FFMPEG_VERSION_PATCH} (from original port file)")
    endif()

endfunction()


function(get_oiio_version)
    get_portfile_path(openimageio vcpkg.json OIIO_PORTFILE_PATH)
    file(READ ${OIIO_PORTFILE_PATH} _OIIO_PORTFILE_CONTENTS)

    set(OIIO_SEMVER_REGEX ".*\"version.*\": \"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)\".*")
    string(REGEX MATCH ${OIIO_SEMVER_REGEX} OIIO_VERSIONS ${_OIIO_PORTFILE_CONTENTS})
    string(REGEX REPLACE ${OIIO_SEMVER_REGEX} "\\1" OIIO_VERSION_MAJOR ${OIIO_VERSIONS})
    string(REGEX REPLACE ${OIIO_SEMVER_REGEX} "\\2" OIIO_VERSION_MINOR ${OIIO_VERSIONS})
    string(REGEX REPLACE ${OIIO_SEMVER_REGEX} "\\3" OIIO_VERSION_PATCH ${OIIO_VERSIONS})
    string(REGEX REPLACE ${OIIO_SEMVER_REGEX} "\\4" OIIO_VERSION_TWEAK ${OIIO_VERSIONS})

    set(OIIO_VERSION_MAJOR ${OIIO_VERSION_MAJOR} CACHE STRING "" FORCE)
    set(OIIO_VERSION_MINOR ${OIIO_VERSION_MINOR} CACHE STRING "" FORCE)
    set(OIIO_VERSION_PATCH ${OIIO_VERSION_PATCH} CACHE STRING "" FORCE)
    set(OIIO_VERSION_TWEAK ${OIIO_VERSION_TWEAK} CACHE STRING "" FORCE)

    # Check if regex match was successful
    if("${OIIO_VERSION_MAJOR}" STREQUAL "" OR "${OIIO_VERSION_MINOR}" STREQUAL "" OR "${OIIO_VERSION_PATCH}" STREQUAL "" OR "${OIIO_VERSION_TWEAK}" STREQUAL "")
        message(FATAL_ERROR "Failed to extract OpenImageIO version from portfile.")
    endif()

    if(${OIIO_PORTFILE_PATH} STREQUAL "${VCPKG_OVERLAYS_DIR}/openimageio/vcpkg.json")
        message(STATUS "OpenImageIO version: ${OIIO_VERSION_MAJOR}.${OIIO_VERSION_MINOR}.${OIIO_VERSION_PATCH}.${OIIO_VERSION_TWEAK} (from overlay port file)")
    else()
        message(STATUS "OpenImageIO version: ${OIIO_VERSION_MAJOR}.${OIIO_VERSION_MINOR}.${OIIO_VERSION_PATCH}.${OIIO_VERSION_TWEAK} (from original port file)")
    endif()
    
endfunction()