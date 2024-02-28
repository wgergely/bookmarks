#ifndef IMAGEUTIL_H
#define IMAGEUTIL_H

#pragma once  // Prevents multiple inclusions

#include <chrono>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <locale>
#include <map>
#include <memory>
#include <optional>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

// Workaround the codecvt deprecation
#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#else
#include <codecvt>
#endif  // _WIN32

#include <OpenImageIO/imagebufalgo.h>
#include <OpenImageIO/imagecache.h>
#include <OpenImageIO/imageio.h>

#ifdef _PYBIND_MODULE
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;
#endif  // _PYBIND_MODULE

std::wstring empty_string = L"";
std::string empty_string_ = "";

/**
 * @brief Converts an input image to an output image with a given size.
 * @param input The input image file path.
 * @param output The output image file path.
 * @param size The size of longest edge of the output image.
 * @param threads The number of threads to use for the conversion (The default
 * is 0 for auto).
 * @param verbose Whether to print verbose messages (false by default).
 * @return 0 if the conversion is successful, 1 otherwise.
 *
 */
int ConvertImage(const std::wstring &input, const std::wstring &output, int size = 0, int threads = 0,
                 bool verbose = false);

/**
 * @brief Converts an input image sequence to an output image sequence with a
 * given size.
 *
 * The input file path should be in the form of
 * "path/to/image.%04d.ext" or "path/to/image.####.ext". The output file path
 * should be in the form of "path/to/image.ext" without the frame number but with
 * the correct extension.
 * @param input The input image sequence file path including a sequence pattern
 * @param output The output image sequence file path without a sequence pattern
 * @param size The size of longest edge of the output image.
 * @param threads The number of threads to use for the conversion (The default
 * is 0 for auto).
 * @param verbose Whether to print verbose messages (false by default).
 * @return 0 if the conversion is successful, 1 otherwise.
 *
 */
int ConvertSequence(const std::wstring &input, const std::wstring &output, int size = 9, int threads = 0,
                    bool verbose = false);
#endif  // IMAGEUTIL_H
