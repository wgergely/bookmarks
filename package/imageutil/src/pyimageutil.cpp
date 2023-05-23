#include <vector>
#include <fstream>
#include <iostream>
#include <cstdio>
#include <cmath>
#include <algorithm>

#include <imageutil.h>


#ifdef BUILD_PYBIND11
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;
#endif


bool is_valid_file(const std::string& f) {
    // Check if file exists and its size isn't too small, or too big
    std::ifstream _f(f, std::ios::binary | std::ios::ate);
    if (!_f.is_open()) {
        std::cerr << "Warning: " << f << " does not exist." << std::endl;
        return false;
    }
    std::size_t size = _f.tellg();
    if (size < (KB * 0.5)) {
        std::cout << "Warning: " << f << " is too small, skipping." << std::endl;
        return false;
    }
    if (size > GB) {
        std::cout << "Warning: " << f << "is too big, skipping." << std::endl;
        return false;
    }
    return true;
}


bool is_locked(const std::string& f) {
    // Check if f is locked
    std::ifstream _f(f + ".lock");
    if (_f.is_open() || _f.good()) {
        std::cout << "Warning: " << f << " is locked. Skipping." << std::endl;
        return true;
    }
    return false;
}


void calc_thumb_width_height(const OIIO::ImageSpec& spec, const int max_size, int* _width, int* _height) {
    // Get the image dimensions
    int width = spec.width;
    int height = spec.height;

    // Calculate the aspect ratio of the image
    float aspect_ratio = (float)width / (float)height;
    bool landscape = aspect_ratio > 1.0;

    if (landscape) {
        *_width = max_size;
        *_height = (float)max_size / aspect_ratio;
    }
    else {
        *_width = (float)max_size * aspect_ratio;
        *_height = max_size;
    }
}


bool _create_lock(const std::string& f) {
    // Create lock file
    std::string lock_path = f + ".lock";
    std::ofstream lock(lock_path);
    if (!lock.good())
    {
        std::cerr << "Warning: Failed to create " << lock_path << std::endl;
        return false;
    }
    return true;
}


bool _remove_lock(const std::string& f) {
    // Remove the lock file
    std::string lock_path = f + ".lock";
    int result = std::remove(lock_path.c_str());
    if (result != 0)
    {
        std::cerr << "Failed to remove " << lock_path << std::endl;
        return false;
    }
    return true;
}



OIIO::ImageBuf get_buf(const std::string& filename, bool debug) {
    if (debug) {
        std::cout << std::endl << "\n\n# Processing " << filename << std::endl;
    }

    // Open the source image
    auto input = OIIO::ImageInput::open(filename);
    if (!input) {
        std::cerr << "Warning: Could not open " << filename << std::endl;
        std::cerr << OIIO::geterror() << std::endl << std::endl;
        return OIIO::ImageBuf();
    }

    // ImageSpec
    const OIIO::ImageSpec& spec = input->spec();

    if (debug) {
        std::cout << "Input image specs:\n" << spec.serialize(OIIO::ImageSpec::SerialText, OIIO::ImageSpec::SerialDetailed);
    }

    // Gather channel information
    std::vector<ChannelInfo> channels;
    std::vector<std::string> rgba_whitelist = { "R", "G", "B", "A" };
    std::vector<std::string> xyz_whitelist = { "X", "Y", "Z" };


    // Get RGBA channels first...
    for (int i = 0; i < spec.nchannels; i++) {
        OIIO::string_view name = spec.channel_name(i);

        if (std::find(rgba_whitelist.begin(), rgba_whitelist.end(), name) == rgba_whitelist.end()) {
            continue;
        }

        ChannelInfo info = ChannelInfo();
        info.channel_format = spec.channelformat(i);
        info.channel_name = name;
        info.channel_index = i;
        channels.push_back(info);

        if (debug) {
            std::cout << "Found channel \"" << info.channel_name << "\" (" << info.channel_format << ", index " << info.channel_index << ")" << std::endl;
        }
    }

    // If that fails, check XYZ channels...
    if (channels.size() == 0) {
        for (int i = 0; i < spec.nchannels; i++) {
            OIIO::string_view name = spec.channel_name(i);

            if (std::find(xyz_whitelist.begin(), xyz_whitelist.end(), name) == xyz_whitelist.end()) {
                continue;
            }

            ChannelInfo info = ChannelInfo();
            info.channel_format = spec.channelformat(i);
            info.channel_name = name;
            info.channel_index = i;
            channels.push_back(info);

            if (debug) {
                std::cout << "Found channel \"" << info.channel_name << "\" (" << info.channel_format << ", index " << info.channel_index << ")" << std::endl;
            }
        }
    }

    // As a last resort, use the first channel of the image
    if (channels.size() == 0) {
        std::cerr << "Warning: " << filename << " has not suitable channels." << std::endl;
        input->close();
        return OIIO::ImageBuf();
    }

    input->close();

    // Create read-only buffer
    OIIO::ImageBuf buf = OIIO::ImageBuf(filename, 0, 0);

    // Leaving this here for posterity but the code doesn't work and
    // has no real performance benefit as far as I can see:
    //
    //for (ChannelInfo info : channels) {
    //    // From the docs:
    //    // Please note that chstart/chend is �advisory� and not guaranteed to be honored by the underlying implementation
    //    if (!buf.read(
    //        0, // subimage
    //        0, // mipmap
    //        info.channel_index, //channel start
    //        info.channel_index + 1, // channel end
    //        true, // force to load data to local buffer storage (instead of image cache)
    //        channel_format // conversion format
    //    )) {
    //        std::cerr << "Warning: Could not read channel \"" << info.channel_name << "\" from " << filename << std::endl;
    //        std::cerr << buf.geterror() << std::endl;
    //        buf.reset();
    //        return OIIO::ImageBuf();
    //    }
    //}

    std::vector<int> channel_indices;
    for (ChannelInfo info : channels) {
        channel_indices.push_back(info.channel_index);
    }

    // Fill vectors in case we don't have 3 separate channels
    if (channel_indices.size() == 1) {
        channel_indices.push_back(channel_indices[0]);
        channel_indices.push_back(channel_indices[0]);
    }
    else if (channel_indices.size() == 2) {
        channel_indices.push_back(channel_indices[1]);
    }

    // Sanity check
    if (!(channel_indices.size() == 3 || channel_indices.size() == 4)) {
        std::cerr << "Warning: Channel size should be 3 or 4, not " << channel_indices.size() << std::endl;
        return OIIO::ImageBuf();
    }

    std::vector<std::string> channel_names = channel_indices.size() == 4 ? std::vector<std::string>{"R", "G", "B", "A"} : std::vector<std::string>{ "R", "G", "B" };

    if (debug) {
        // Print the contents of the vector
        std::cout << "Channel names: " << "(" << channel_names.size() << ")";
        for (int i = 0; i < channel_names.size(); ++i) {
            std::cout << channel_names[i] << ' ';
        }
        std::cout << std::endl;

        std::cout << "Channel indices: " << "(" << channel_indices.size() << ")";
        for (int i = 0; i < channel_indices.size(); ++i) {
            std::cout << channel_indices[i] << ' ';
        }
        std::cout << std::endl;
    }

    if (spec.nchannels == channel_names.size()) {
        for (int i = 0; i < channel_names.size(); ++i) {
            if (channel_names[i] != spec.channel_name(i)) {
                // Discard unused channels
                if (debug) {
                    std::cout << "Copying channels... " << std::endl;
                }
                if (!OIIO::ImageBufAlgo::channels(
                    buf, // destination
                    buf, // source
                    channel_indices.size(), // nchannels
                    channel_indices.data(), //channel order
                    {}, // channel values,
                    channel_names.data(), // new channel names,
                    false, // shuffle channels
                    0 // threads
                )) {
                    std::cerr << "Warning: Could not copy channels." << std::endl;
                    std::cerr << OIIO::geterror() << std::endl;
                    buf.reset();
                    return OIIO::ImageBuf();
                }
                else {
                    if (debug) {
                        std::cout << "Channels copied: " << buf.spec().serialize(OIIO::ImageSpec::SerialText, OIIO::ImageSpec::SerialBrief);
                    }
                }
            }
        }
    }

    // Flatten deep images
    if (spec.deep) {
        if (debug) {
            std::cout << "Flattening deep image..." << std::endl;
        }
        OIIO::ImageBuf _buf = OIIO::ImageBuf();
        if (!OIIO::ImageBufAlgo::flatten(_buf, buf) && debug) {
            std::cout << "Warning: Could not flatten image." << std::endl;
            if (buf.has_error()) {
                std::cout << buf.geterror() << std::endl;
            }
        }
        else {
            buf = _buf;
        }
    }

    // Convert colour
    std::string colorspace = spec.get_string_attribute("oiio:ColorSpace", "sRGB");
    if (colorspace != "sRGB") {
        if (debug) {
            std::cout << "Converting colors..." << std::endl;
        }
        if (!OIIO::ImageBufAlgo::colorconvert(buf, buf, colorspace, "sRGB") && debug) {
            std::cout << "Warning: Could not convert " << colorspace << " to sRGB" << std::endl;
            if (buf.has_error()) {
                std::cout << buf.geterror() << std::endl;
            }
        }
    }

    return buf;
}


bool convert_image(
    const std::string& input_image,
    const std::string& output_image,
    const int max_size,
    bool debug
) {
    // Verify image
    if (!is_valid_file(input_image)) {
        return false;
    }

    // Check if source or destination images are not locked
    if (is_locked(output_image)) {
        return false;
    }
    else {
        // Create lock but return if lock can't be created
        if (!_create_lock(output_image)) {
            return false;
        }
    }

    // Load source image
    OIIO::ImageBuf buf = get_buf(input_image, debug);
    if (!buf.initialized()) {
        _remove_lock(output_image);
        return false;
    }

    // Get spec
    OIIO::ImageSpec _spec = buf.spec();

    // Check if it is needed to do resize
    int _max_edge = (int)std::max(_spec.width, _spec.height);
    if (_max_edge > 25000 || max_size > 25000) {
        std::cout << "Warning: Image too large, skipping." << std::endl;
        _remove_lock(output_image);
        return false;
    }

    bool needs_resize = _max_edge != (int)max_size;

    // Skip resizing if max_size is smaller than 1
    OIIO::ImageBuf _buf;
    if (needs_resize && max_size > 0) {
        // Create destination image size
        int t_width, t_height;
        calc_thumb_width_height(_spec, max_size, &t_width, &t_height);

        // Get region of interest for thumbnail image
        OIIO::ROI roi = OIIO::ROI(
            0, t_width, // x begin/end
            0, t_height, // y begin/end
            0, 1, //z begin/end
            0, buf.nchannels() // channel being/end
        );

        // The buf the source image will have to be fit into
        _buf = OIIO::ImageBuf(
            OIIO::ImageSpec(t_width, t_height, buf.nchannels(), OIIO::TypeDesc::FLOAT)
        );


        // Fit source
        if (debug) {
            std::cout << std::endl << "Resizing..." << std::endl;
        }
        if (!OIIO::ImageBufAlgo::fit(
            _buf,
            buf,
            "gaussian", // filter name
            1, // filter width
            "width", // fill mode
            roi
        )) {
            std::cerr << "Warning: Could not resize the image" << std::endl;
            _buf.reset();
            buf.reset();
            _remove_lock(output_image);
            return false;
        }
    } else {
        if (debug) {
            std::cout << std::endl << "Skipping resize..." << std::endl;
        }
        _buf = buf;
    }

    // We're removing all extra attributes so the original metadata doesn't
    // propagate to the new converted images
    OIIO::ImageSpec& spec = _buf.specmod();
    spec.extra_attribs.clear();

    if (debug) {
        std::cout << std::endl << "Out image:" << std::endl;
        std::cout << _buf.spec().serialize(OIIO::ImageSpec::SerialText, OIIO::ImageSpec::SerialDetailed);
    }

    // Write thumbnail file
    if (debug) {
        std::cout << "Writing " << output_image << std::endl;
    }
    if (!_buf.write(output_image)) {
        std::cerr << "Warning: Could not write " << output_image << std::endl;
        if (_buf.has_error()) {
            std::cout << _buf.geterror() << std::endl;
        }
        _buf.reset();
        buf.reset();
        _remove_lock(output_image);
        return false;
    }
    _buf.reset();
    buf.reset();
    _remove_lock(output_image);
    return true;
}


bool convert_images(
    const std::vector<std::string>& input_images,
    const std::vector<std::string>& output_images,
    const int max_size,
    bool debug
) {
    // Ensure that the number of input and output images matches
    if (input_images.size() != output_images.size()) {
        return false;
    }

    // Iterate over each input/output image pair
    for (size_t i = 0; i < input_images.size(); ++i) {
        bool success = convert_image(input_images[i], output_images[i], max_size, debug);
        if (!success) {
            return false;
        }
    }

    return true;
}




// Create Python bindings
#ifdef BUILD_PYBIND11

bool py_convert_image(
    const std::string& input_image,
    const std::string& output_image,
    const int max_size,
    bool debug,
    bool release_gil
) {
    // GIL is held when called from Python code. Release GIL before
    // calling into (potentially long-running) C++ code
    if (release_gil) {
        py::gil_scoped_release release;
    }
    return convert_image(input_image, output_image, max_size, debug);
}

bool py_convert_images(
    const std::vector<std::string>& input_images,
    const std::vector<std::string>& output_images,
    const int max_size,
    bool debug,
    bool release_gil
) {
    // GIL is held when called from Python code. Release GIL before
    // calling into (potentially long-running) C++ code
    if (release_gil) {
        py::gil_scoped_release release;
    }
    try {
        return convert_images(input_images, output_images, max_size, debug);
    }
    catch (...) {
        // Exception occurred while calling convert_images
        return false;
    }
}

PYBIND11_MODULE(pyimageutil, m)
{
    m.doc() = "OpenImageIO C++ helper library for Bookmarks.";
    m.def(
        "convert_image",
        &py_convert_image,
        py::arg("input_image").none(false),
        py::arg("output_image").none(false),
        py::arg("max_size") = 512,
        py::arg("debug") = false,
        py::arg("release_gil") = true,
        py::return_value_policy::copy,
        "Create a thumbnail from `input_image` and save it as `output_image`"
    );
    m.def(
        "convert_images",
        &py_convert_images,
        py::arg("input_images").none(false),
        py::arg("output_images").none(false),
        py::arg("max_size") = 512,
        py::arg("debug") = false,
        py::arg("release_gil") = true,
        py::return_value_policy::copy,
        "Create thumbnails from `input_images` and save them as `output_images`"
    );
}

#endif