#ifndef IMAGEUTIL_H
#define IMAGEUTIL_H

#pragma once // Prevents multiple inclusions

#include <OpenImageIO/imagebufalgo.h>
#include <OpenImageIO/imagecache.h>
#include <OpenImageIO/imageio.h>
#include <OpenImageIO/ustring.h>

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <variant>
#include <vector>

#ifdef _PYBIND_MODULE
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;
#endif // _PYBIND_MODULE

std::wstring empty_string = L"";
std::string empty_string_ = "";

/**
 * @brief Checks if the output image is up to date, or needs re-conversion.
 * @param input The input image file path.
 * @param output The output image file path.
 * @return 1 if the output image is up to date, 0 otherwise.
 */
int IsUpToDate(const std::wstring &input, const std::wstring &output, bool verbose = false);

/**
 * @brief Converts an input image to an output image with a given size.
 * @param input The input image file path.
 * @param output The output image file path.
 * @param source_color_space The source color space of the input image. Pass "" to use the hint from the OIIO:ColorSpace attribute.
 * @param target_color_space The target color space of the output image.
 * @param size The size of longest edge of the output image.
 * @param threads The number of threads to use for the conversion (The default
 * is 0 for auto).
 * @param verbose Whether to print verbose messages (false by default).
 * @return 0 if the conversion is successful, 1 otherwise.
 *
 */
int ConvertImage(
    const std::wstring &input,
    const std::wstring &output,
    const std::wstring &source_color_space,
    const std::wstring &target_color_space,
    int size = 0,
    int threads = 0,
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
 * @param source_color_space The source color space of the input image. Pass "" to use the hint from the OIIO:ColorSpace attribute.
 * @param target_color_space The target color space of the output image.
 * @param size The size of longest edge of the output image.
 * @param threads The number of threads to use for the conversion (The default
 * is 0 for auto).
 * @param verbose Whether to print verbose messages (false by default).
 * @return 0 if the conversion is successful, 1 otherwise.
 *
 */
int ConvertSequence(
    const std::wstring &input,
    const std::wstring &output,
    const std::wstring &source_color_space,
    const std::wstring &target_color_space,
    int size = 0,
    int threads = 0,
    bool verbose = false);
#endif // IMAGEUTIL_H
