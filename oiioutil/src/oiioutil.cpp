#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <sys/stat.h>
#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <algorithm>
#include <cctype>
#include <cmath>

#include <OpenImageIO/imageio.h>
#include <OpenImageIO/imagebuf.h>
#include <OpenImageIO/imagebufalgo.h>
#include <OpenImageIO/imagecache.h>

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Windows does not define the S_ISREG and S_ISDIR macros in stat.h, so we do.
// We have to define _CRT_INTERNAL_NONSTDC_NAMES 1 before #including sys/stat.h
// in order for Microsoft's stat.h to define names like S_IFMT, S_IFREG, and S_IFDIR,
// rather than just defining  _S_IFMT, _S_IFREG, and _S_IFDIR as it normally does.
#define _CRT_INTERNAL_NONSTDC_NAMES 1
#include <sys/stat.h>
#if !defined(S_ISREG) && defined(S_IFMT) && defined(S_IFREG)
#define S_ISREG(m) (((m)&S_IFMT) == S_IFREG)
#endif
#if !defined(S_ISDIR) && defined(S_IFMT) && defined(S_IFDIR)
#define S_ISDIR(m) (((m)&S_IFMT) == S_IFDIR)
#endif

// Define a custom comparison function for use with std::equal()
bool equal_ignore_case(char a, char b)
{
    // Convert both characters to lowercase and compare them
    return std::tolower(a) == std::tolower(b);
}

// Helper function to get the scaled image specification
OIIO::ImageSpec _get_scaled_spec(const OIIO::ImageSpec &source_spec, int size)
{
    // Calculate the scaling factor
    float factor = float(size) / float(std::max(source_spec.width, source_spec.height));
    int w = source_spec.width * factor;
    int h = source_spec.height * factor;

    // If the number is odd, round it down to the nearest even number
    if (w % 2 != 0)
    {
        w -= 1;
    }
    if (h % 2 != 0)
    {
        h -= 1;
    }

    OIIO::ImageSpec s = OIIO::ImageSpec(int(w), int(h), 4, OIIO::TypeDesc::UINT8);
    s.channelnames = {"R", "G", "B", "A"};
    s.alpha_channel = 3;
    s.attribute("oiio:ColorSpace", "sRGB");
    s.attribute("oiio:Gamma", "0.454546");
    return s;
}

// Helper function to shuffle channels of the image
OIIO::ImageBuf _shuffle_channels(const OIIO::ImageBuf &buf, const OIIO::ImageSpec &source_spec)
{
    // Let's check if the RGBA channels exist
    if (
        source_spec.channelindex("R") > -1 &&
        source_spec.channelindex("G") > -1 &&
        source_spec.channelindex("B") > -1 &&
        source_spec.channelindex("A") > -1)
    {
        return OIIO::ImageBufAlgo::channels(
            buf,
            4,
            {source_spec.channelindex("R"), source_spec.channelindex("G"), source_spec.channelindex("B"), source_spec.channelindex("A")},
            {0, 0, 0, 0},
            {"R", "G", "B", "A"});
    }
    // Let's check if the RGB channels exist
    if (
        source_spec.channelindex("R") > -1 &&
        source_spec.channelindex("G") > -1 &&
        source_spec.channelindex("B") > -1)
    {
        return OIIO::ImageBufAlgo::channels(
            buf,
            4,
            {source_spec.channelindex("R"), source_spec.channelindex("G"), source_spec.channelindex("B"), -1},
            {0, 0, 0, 1.0}, // fill alpha with solid
            {"R", "G", "B", "A"});
    }
    // In all other cases use the first channel
    return OIIO::ImageBufAlgo::channels(
        buf,
        4,
        {0, 0, 0, -1},
        {0, 0, 0, 1.0},
        {"R", "G", "B", "A"});
}

// Helper function to resize the image
OIIO::ImageBuf _resize(const OIIO::ImageBuf &buf, const OIIO::ImageSpec &destination_spec)
{
    return OIIO::ImageBufAlgo::resample(buf, true, destination_spec.roi());
}

// Helper function to flatten the image
OIIO::ImageBuf _flatten(const OIIO::ImageBuf &buf, const OIIO::ImageSpec &source_spec)
{
    if (source_spec.get_int_attribute("deep", -1) != 1)
    {
        return buf;
    }
    if (source_spec.deep)
    {
        return OIIO::ImageBufAlgo::flatten(buf);
    }
    return buf;
}

// Helper function to convert the color profile of the image
OIIO::ImageBuf _colorconvert(const OIIO::ImageBuf &buf, const OIIO::ImageSpec &source_spec)
{
    if (source_spec.get_int_attribute("oiio:Movie") == 1)
    {
        return buf;
    }
    std::string colorspace = source_spec.get_string_attribute("oiio:ColorSpace");
    try
    {
        if (colorspace == "linear")
        {
            return OIIO::ImageBufAlgo::colorconvert(buf, colorspace, "sRGB");
        }
    }
    catch (...)
    {
        std::cerr << "Could not convert the color profile" << std::endl;
    }
    return buf;
}

OIIO::ImageBuf get_buf(const std::string &filename, int subimage)
{
    if (filename.find('.') == std::string::npos)
    {
        std::cerr << "Does not look like a file: " << filename << std::endl;
        return OIIO::ImageBuf();
    }

    std::string ext = filename.substr(filename.find_last_of('.') + 1);
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    if (!OIIO::is_imageio_format_name(ext))
    {
        std::cerr << "Unsupported file format: " << ext << std::endl;
        return OIIO::ImageBuf();
    }

    auto i = OIIO::ImageInput::create(ext);
    if (!i || !i->valid_file(filename.c_str()))
    {
        i->close();
        std::cerr << filename << " doesn't seem like a valid file" << std::endl;
        std::cerr << OIIO::geterror() << std::endl;
        return OIIO::ImageBuf();
    }
    else
    {
        i->close();
    }

    OIIO::ImageBuf buf = OIIO::ImageBuf::ImageBuf(filename.c_str(), subimage, 0);
    if (buf.has_error())
    {
        std::cerr << buf.geterror() << std::endl;
        return OIIO::ImageBuf();
    }

    return buf;
}

// Create a lock file for the given filename
bool create_lock_file(const std::string &filename)
{
    // Set up the lock file name
    std::string lock_file = filename + ".lock";

    // Check if the lock file already exists
    std::ifstream lock_stream(lock_file);
    if (lock_stream.good())
    {
        std::cerr << "Lock file already exists: " << lock_file << std::endl;
        return false;
    }

    // Create the lock file
    std::ofstream lock_file_stream(lock_file);
    if (!lock_file_stream.good())
    {
        std::cerr << "Failed to create lock file: " << lock_file << std::endl;
        return false;
    }

    return true;
}

// Remove the lock file for the given filename
void remove_lock_file(const std::string &filename)
{
    // Set up the lock file name
    std::string lock_file = filename + ".lock";

    // Remove the lock file
    int result = std::remove(lock_file.c_str());
    if (result != 0)
    {
        std::cerr << "Failed to remove lock file: " << lock_file << std::endl;
    }
}

// Check if the file exists
bool _is_file(char *filename)
{
    struct stat buffer;
    return (stat(filename, &buffer) == 0);
}

bool make_thumbnail(char *source_c, char *destination_c, int size)
{
    // Parse the source and destination file paths
    std::string source = source_c;
    std::string destination = destination_c;

    const std::vector<std::string> accepted_codecs = {"h.264", "h264", "mpeg-4", "mpeg4"};

    // Check if the source file exists
    if (!_is_file(source_c))
    {
        std::cerr << "Source file does not exist: " << source << std::endl;
        return 1;
    }

    if (!create_lock_file(destination_c))
    {
        return 1;
    }

    OIIO::ImageBuf buf = get_buf(source_c, 0);

    if (!buf.initialized())
    {
        remove_lock_file(destination_c);
        std::cerr << "Failed to get the image buffer" << std::endl;
        return 1;
    }

    // Get the source image spec
    OIIO::ImageSpec source_spec = buf.spec();
    // Remove the ICCProfile
    source_spec.attribute("ICCProfile", "");
    source_spec.erase_attribute("ICCProfile");

    if (source_spec.get_int_attribute("oiio:Movie", -1) == 1)
    {
        // Load the middle frame of the video
        buf = get_buf(source_c, int(buf.nsubimages() / 2));

        bool is_gif = source_spec.get_int_attribute("gif:LoopCount", -1) >= 0;

        // I'm having issues working with very short movie files that contain only a couple of frames,
        // so, let's ignore those ( except gifs, those are fine)
        if (!is_gif && source_spec.get_int_attribute("oiio:subimages", -1) <= 2)
        {
            std::cerr << "Movie file is too short: " << source << std::endl;
            remove_lock_file(destination_c);
            return 1;
        }

        // [BUG] Not all codec formats are supported by ffmpeg. There does
        // not seem to be (?) error handling and an unsupported codec will
        // crash ffmpeg and the rest of the app.
        std::string codec_name = source_spec.get_string_attribute("ffmpeg:codec_name", "");
        std::string codec_name_lower = codec_name;

        // Check if the codec is supported
        if (!is_gif && !codec_name.empty())
        {
            std::transform(codec_name.begin(), codec_name.end(), codec_name_lower.begin(), [](unsigned char c)
                           { return std::tolower(c); });
            if (find(accepted_codecs.begin(), accepted_codecs.end(), codec_name_lower) != accepted_codecs.end())
            {
                std::cerr << "Unsupported movie format: " << codec_name << std::endl;
                remove_lock_file(destination_c);
                return 1;
            }
        }
    }

    // Get the scaled destination image spec
    OIIO::ImageSpec destination_spec = _get_scaled_spec(source_spec, size);
    if (size != -1)
    {
        buf = _resize(buf, destination_spec);
    }
    buf = _shuffle_channels(buf, source_spec);
    buf = _flatten(buf, source_spec);
    buf = _colorconvert(buf, source_spec);
    buf.set_write_format(OIIO::TypeDesc::UINT8);

    OIIO::ImageSpec spec = buf.spec();

    // On some dpx images I'm getting "GammaCorrectedinf"
    std::string cspace = source_spec.get_string_attribute("oiio:ColorSpace", "");
    std::string cspace_lower = cspace;
    std::transform(cspace.begin(), cspace.end(), cspace_lower.begin(), [](unsigned char c)
                   { return std::tolower(c); });
    if (cspace.find("gammacorrectedinf") != std::string::npos)
    {
        spec.attribute("oiio:ColorSpace", "sRGB");
        spec.attribute("oiio:Gamma", "0.454545");
    }

    // Write the image
    if (!buf.write(destination, OIIO::TypeDesc::UINT8))
    {
        std::cerr << "Failed to write the image" << std::endl;
        remove_lock_file(destination_c);
        return 1;
    }
    remove_lock_file(destination_c);
    return 0;
}

// Create Python bindings
PYBIND11_MODULE(bookmarks_oiio, m)
{
    m.doc() = "OpenImageIO C++ helper library.";
    m.def(
        "make_thumbnail",
        &make_thumbnail,
        py::arg("source"), py::arg("destination"), py::arg("size"),
        py::return_value_policy::copy,
        "Create a thumbnail from a source image");
}