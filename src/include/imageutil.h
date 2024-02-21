#ifndef IMAGEUTIL_H
#define IMAGEUTIL_H

#include <string>

#include <OpenImageIO/imagecache.h>
#include <OpenImageIO/imageio.h>
#include <OpenImageIO/imagebuf.h>
#include <OpenImageIO/imagebufalgo.h>


/**
 * @brief Structure that holds information about a single channel in an image
 * 
 * This struct holds information about a single channel in an image file, including its name, format, and index.
 */
struct ChannelInfo {
    OIIO::string_view channel_name; ///< The name of the channel
    OIIO::TypeDesc channel_format; ///< The format of the channel data
    int channel_index; ///< The index of the channel within the image file
};


constexpr long long KB = 1024;
constexpr long long MB = 1024LL * 1024LL;
constexpr long long GB = MB * 1024LL;


/**
 * @brief Checks if a file is valid.
 *
 * This function checks if the file exists and if its size is within
 * the acceptable range.
 * 
 * @param f A string reference to the file path to be checked
 * 
 * @return `true` if the file is valid, `false` otherwise
 */
bool is_valid_file(const std::string& f);


/**
* @brief Determines if the file is locked
*
* @param f A string reference to the file path to be checked
*
* @return bool Returns `true` if the file is locked, otherwise `false`
*/
bool is_locked(const std::string& f);


/**
 * @brief Calculates the width and height of a thumbnail.
 * 
 * @param spec ImageSpec containing image dimensions.
 * @param max_size The maximum size the thumbnail can be.
 * @param _width A pointer to the width of the thumbnail.
 * @param _height A pointer to the height of the thumbnail.
 * 
 * The function calculates the aspect ratio of the image and uses this
 * information to determine the width and height of the thumbnail. The thumbnail
 * will never exceed the `max_size` parameter in either dimension.
 */
void calc_thumb_width_height(const OIIO::ImageSpec& spec, const int max_size, int* _width, int* _height);


/**
* @brief Creates a lock file.
*
* Given a file path f, the function creates a lock file at f + ".lock".
*
* @param f Path to the file that the lock file will be created for
*
* @returns true if lock file creation was successful, false otherwise.
*/
bool _create_lock(const std::string& f);


/**
* @brief Removes the lock file.#
*
* @param f The path of the file to remove the lock from.
*
* @return True if the lock was removed successfully, false otherwise.
*/
bool _remove_lock(const std::string& f);


/**
 * @brief Load an RGB(A) OIIO ImageBuf from a file
 * 
 * @param filename The path to the input file
 * @param debug Optional flag to print debug information during processing
 * 
 * @return An OIIO ImageBuf containing the image data, or an uninitiaiized ImageBuf if loading fails
 */
OIIO::ImageBuf get_buf(const std::string& filename, bool debug = false);


/**
 * @brief Create a thumbnail from a source file and save it to destination.
 * 
 * @param input_image A string path to the input file
 * @param output_image A string path to the output (thumbnail) file
 * @param max_size The size the output image should fit in
 * @param debug Optional flag to print debug information during processing 
 * 
 * @return `true` on success, `false` on failiure
 */
bool convert_image(const std::string& input_image, const std::string& output_image, const int max_size = 512, bool debug = false);

/**
 * @brief Create a thumbnails from a list of source files and save it to the destinations.
 *
 * @param input_image A string path to the input file
 * @param output_image A string path to the output (thumbnail) file
 * @param max_size The size the output image should fit in
 * @param debug Optional flag to print debug information during processing
 *
 * @return `true` on success, `false` on failiure
 */
bool convert_images(const std::vector<std::string>& input_images, const std::vector<std::string>& output_images, const int max_size = 512, bool debug = false);



#ifdef BUILD_PYBIND11

/**
 * @brief PyBind11 wrapper function for make_thumbnail
 * 
 * @return `true` on success, `false` on failiure
*/
bool py_convert_image(const std::string& input_image, const std::string& output_image, const int max_size = 512, bool debug = false);



#endif


#endif

