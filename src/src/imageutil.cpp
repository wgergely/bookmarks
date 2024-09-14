#include "imageutil.h"

#include "commandlineparser.h"
#include "stringconverter.h"

using namespace OIIO;

std::mutex io_mutex;

ImageCache *CreateCache() {
    static std::unique_ptr<ImageCache, void (*)(ImageCache *)> image_cache(
        ImageCache::create(true), [](ImageCache *ptr) { ImageCache::destroy(ptr); }  // Custom deleter as a lambda
    );
    static std::once_flag flag;
    std::call_once(flag, []() {
        image_cache->attribute("forcefloat", 0);
        image_cache->attribute("max_memory_MB", 2048.0f);
    });
    return image_cache.get();
}

bool RemoveLockFile(const std::wstring &input) {
    std::lock_guard<std::mutex> lock(io_mutex);
    {
        std::wstring lockPath = input + L".lock";
        std::filesystem::remove(lockPath);
        if (std::filesystem::exists(lockPath)) {
            std::cerr << "[Error] Could not remove lock file: " << StringConverter::to_string(lockPath) << std::endl;
            return false;
        }
        return true;
    }
}

bool CreateLockFile(const std::wstring &input) {
    std::lock_guard<std::mutex> lock(io_mutex);
    {
        std::wstring lockPath = input + L".lock";

        // Return false if the lock file already exists
        if (std::filesystem::exists(lockPath)) {
            // Get the last modified time of the file
            auto last_modified_time = std::filesystem::last_write_time(lockPath);

            // Convert last_modified_time to time_point compatible with system_clock
            auto last_modified_time_tp = std::chrono::time_point_cast<std::chrono::system_clock::duration>(
                last_modified_time - std::filesystem::file_time_type::clock::now() + std::chrono::system_clock::now());

            // Get the current time
            auto now = std::chrono::system_clock::now();

            // Calculate the duration since last modification
            auto duration_since_last_modified = now - last_modified_time_tp;

            // Convert the duration to minutes
            auto minutes_since_last_modified =
                std::chrono::duration_cast<std::chrono::minutes>(duration_since_last_modified).count();

            // Check if it has been more than 5 minutes
            // if the file is older than 5 minutes, remove it
            if (minutes_since_last_modified >= 5) {
                std::filesystem::remove(lockPath);
            } else {
                return false;
            }
        }

        std::wofstream lockFile(lockPath, std::ios::out | std::ios::trunc);

        if (!lockFile.is_open()) {
            return false;
        }
        // Put machine name and process pid in the lock file
        lockFile << "Locked." << std::endl;
        lockFile.close();
        return true;
    }
}

void WriteProgress(const std::string &message, int verbose) {
    std::lock_guard<std::mutex> lock(io_mutex);
    {
        if (!verbose) {
            return;
        }
        std::cout << "[Progress] " << message << std::endl;
    }
}

void WriteError(const std::string &message, const std::string &input, std::string &errstring) {
    std::lock_guard<std::mutex> lock(io_mutex);
    {
        std::cout << "[Error] " << message << std::endl;
        std::cout << "    Path: " << input << std::endl;
        if (!errstring.empty()) {
            std::cout << "    " << errstring << std::endl;
        }
        if (has_error()) {
            std::cout << "   " << geterror() << std::endl;
        }
    }
}


int ConvertImage(const std::wstring &input, const std::wstring &output, int size, int threads, bool verbose) {

    int r;
    std::string input_ = StringConverter::to_string(input);
    std::string output_ = StringConverter::to_string(output);

    WriteProgress(">>> Converting image: " + input_, verbose);

    // Check if the intput is a valid file that exists
    if (!std::filesystem::exists(input) || !std::filesystem::is_regular_file(input)) {
        WriteError("Input file does not exist", input_, empty_string_);
        return 1;
    }

    // Attempt to open the input file
    auto in = ImageInput::open(input);
    if (!in) {
        if (has_error()) {
            WriteError("Could not create ImageInput", input_, geterror());
        };
        return 1;
    }
    if (in->has_error()) {
        if (!in->close()) {
            WriteError("Could not close ImageInput", input_, in->has_error() ? in->geterror() : empty_string_);
        };
        WriteError("Could not open ImageInput", input_, in->has_error() ? in->geterror() : empty_string_);
        return 1;
    }

    // Get the image spec
    const ImageSpec &spec = in->spec();

    // Output image size
    if (size == 0) {
        size = std::max(spec.width, spec.height);
    }

    WriteProgress("Input specs: ", verbose);
    WriteProgress(spec.serialize(ImageSpec::SerialText, ImageSpec::SerialDetailed), verbose);

    // Find the best matching miplevel
    int miplevel = 0;
    int best_match_miplevel = -1;
    int largest_miplevel = 0;

    ImageSpec largest_spec;

    WriteProgress("Finding best matching mipmap level...", verbose);
    while (in->seek_subimage(0, miplevel)) {
        if (spec.width >= size && spec.height >= size) {
            // Check if this is the first match or a smaller match than the current
            // best
            if (best_match_miplevel == -1 || (spec.width < largest_spec.width && spec.height < largest_spec.height)) {
                best_match_miplevel = miplevel;
                largest_spec = spec;
            }
        }
        // Always update the largest mipmap level in case we don't find a match
        largest_miplevel = miplevel;
        miplevel++;
    }

    if (best_match_miplevel != -1) {
        // Found a suitable mipmap level larger than the target size
        WriteProgress("Mipmap level " + std::to_string(best_match_miplevel) + " with size " +
                          std::to_string(largest_spec.width) + "x" + std::to_string(largest_spec.height),
                      verbose);
    } else {
        // No suitable mipmap found; use the largest mipmap level
        best_match_miplevel = 0;
    }

    // Read ImageBuf
    ImageBuf buf_(input_, 0, best_match_miplevel);
    if (buf_.has_error()) {
        WriteError("Error reading image", input_, buf_.has_error() ? buf_.geterror() : empty_string_);
        return 1;
    }

    // Check the number of subimages
    int best_subimage = 0;
    int nsubimages = buf_.nsubimages();
    if (nsubimages > 1) {
        best_subimage = (int)((float)nsubimages / 2.0f);
    }

    if (best_subimage != 0) {
        WriteProgress("Resetting subimage to " + std::to_string(best_subimage), verbose);
        buf_.reset(input_, best_subimage, best_match_miplevel);
        if (buf_.has_error()) {
            WriteError("Error resetting subimage", input_, buf_.has_error() ? buf_.geterror() : empty_string_);
            return 1;
        }
    }

    // Channel logic
    std::vector<int> channel_indices = {0, 0, 0, -1};
    std::vector<float> fill_values = {0.3f, 0.3f, 0.3f, 1.0f};  // Default fill values for RGBA

    for (int i = 0; i < spec.nchannels; i++) {
        WriteProgress("Finding suitable channels: " + spec.channelnames[i], verbose);

        if (spec.channelnames[i] == "R" || spec.channelnames[i] == "Y" || spec.channelnames[i] == "L" || spec.channelnames[i] == "RY") {
            channel_indices[0] = i;
        }

        if (spec.channelnames[i] == "G") {
            channel_indices[1] = i;
        }

        if (spec.channelnames[i] == "B") {
            channel_indices[2] = i;
        }

        if (spec.channelnames[i] == "A") {
            channel_indices[3] = i;
        }
    }

    WriteProgress("Using channel indices: ", verbose);
    if (verbose) {
        for (const auto &index : channel_indices) {
            WriteProgress("    " + std::to_string(index), verbose);
        }
    }

    WriteProgress("Shuffling channels...", verbose);
    r = ImageBufAlgo::channels(buf_, buf_, channel_indices.size(), channel_indices, fill_values);
    if (!r || buf_.has_error()) {
        WriteError("Could not shuffle channels", input_, buf_.has_error() ? buf_.geterror() : empty_string_);
        return 1;
    }

    // spec
    ImageSpec spec_ = buf_.spec();

    // Flatten if deep
    if (spec_.deep) {
        WriteProgress("Flattening deep image...", verbose);
        r = ImageBufAlgo::flatten(buf_, buf_);
        if (!r || buf_.has_error()) {
            WriteError("Could not flatten deep image. Continuing...", input_,
                       buf_.has_error() ? buf_.geterror() : empty_string_);
        }
    }

    // Calculate the output size
    int out_width;
    int out_height;

    if (size == -1) {
        out_width = spec_.width;
        out_height = spec_.height;
    } else {
        float _min_size = std::min(spec_.width, spec_.height);
        float _max_size = std::max(spec_.width, spec_.height);
        float aspect = _max_size / _min_size;

        if (spec_.width > spec_.height) {
            out_width = size;
            out_height = (int)(size / aspect);
        } else {
            out_height = size;
            out_width = (int)(size * aspect);
        }
    }

    // Make sure both the output width and height are even
    if (out_width % 2 != 0) {
        out_width++;
    }
    if (out_height % 2 != 0) {
        out_height++;
    }

    WriteProgress("Output size: " + std::to_string(out_width) + "x" + std::to_string(out_height), verbose);
    ROI out_roi = ROI(0, out_width,              // x begin/end
                      0, out_height,             // y begin/end
                      0, 1,                      // z begin/end
                      0, channel_indices.size()  // channel being/end
    );

    ImageSpec out_spec = ImageSpec(out_roi, TypeDesc::UINT8);

    // Input image byte size
    int _bsize;
    try {
        _bsize = std::filesystem::file_size(input);
    } catch (std::exception &e) {
        _bsize = 0;
    }

    out_spec.attribute("SourceByteSize", std::to_string(_bsize));
    out_spec.attribute("oiio:ColorSpace", "sRGB");

    ImageBuf out_buf(out_spec);

    WriteProgress("Output image spec: ", verbose);
    WriteProgress(out_spec.serialize(ImageSpec::SerialText, ImageSpec::SerialDetailed), verbose);

    if (size != 0 && (out_width != spec_.width || out_height != spec_.height)) {
        WriteProgress("Resizing image...", verbose);
        r = ImageBufAlgo::fit(out_buf, buf_, "gaussian", 1.0f, "width", out_roi, threads);
        if (!r || out_buf.has_error()) {
            WriteError("Could not resize image", input_, out_buf.has_error() ? out_buf.geterror() : empty_string_);
            return 1;
        }
    } else {
        out_buf.copy(buf_);
    }

    // Color convert
    std::string spec_color_space = spec_.get_string_attribute("oiio:ColorSpace", "sRGB");
    if (spec_color_space != "sRGB") {
        WriteProgress("Converting colors...", verbose);

        r = ImageBufAlgo::colorconvert(out_buf, out_buf, spec_color_space, "sRGB", true, "", "", nullptr, out_roi,
                                       threads);
        if (!r || out_buf.has_error()) {
            WriteError("Failed to convert color profile. Continuing...", input_,
                       out_buf.has_error() ? out_buf.geterror() : empty_string_);
        }
    }

    WriteProgress("Writing " + output_, verbose);
    out_buf.make_writeable(true);
    out_buf.set_write_format(TypeDesc::UINT8);
    r = out_buf.write(output_);

    // Check that the output file exists and not the file size is not zero
    if (!std::filesystem::exists(output) || std::filesystem::file_size(output) == 0) {
        // Remove the output file

        WriteError("Malformed output file, removing...", input_,
                   out_buf.has_error() ? out_buf.geterror() : empty_string_);
        r = std::filesystem::remove(output);
        if (!r) {
            WriteError("Could not remove malformed output file", input_, empty_string_);
            return 1;
        }
        return 1;
    }

    if (!r || out_buf.has_error()) {
        WriteError("Could not write output", output_, out_buf.has_error() ? out_buf.geterror() : empty_string_);
        return 1;
    }

    WriteProgress("Finished converting " + input_, verbose);
    return 0;
};

std::optional<std::wregex> ConvertInputToRegex(const std::wstring &input, bool verbose) {
    std::filesystem::path _input_path(input);
    std::wstring _parent = _input_path.parent_path().wstring();
    std::wstring input_re = input;

    // Escape special regex characters in the input string
    std::wstring special_chars = L".^$*+?()[]{}|\\";
    for (const auto &c : special_chars) {
        std::wstring str_to_find(1, c);
        std::wstring replacement = L"\\" + str_to_find;
        size_t pos = 0;
        while ((pos = _parent.find(str_to_find, pos)) != std::wstring::npos) {
            _parent.replace(pos, 1, replacement);
            pos += replacement.length();  // Move past the inserted backslash
        }
    }

    std::wstring stem = _input_path.stem();

    // Substitute regex patterns
    std::wsmatch match;
    std::wregex re_printf(L".*?%0(\\d{1})d.*?");
    std::wregex re_hash(L".*?(#+).*?");

    if (std::regex_match(stem, match, re_printf)) {
        std::wstring n = std::to_wstring(match[1].length());
        WriteProgress("Found padding: " + StringConverter::to_string(n), verbose);
        stem = std::regex_replace(stem, std::wregex(L"%0(\\d{1})d"), L"(\\d{$1})");
    } else if (std::regex_match(stem, match, re_hash)) {
        std::wstring n = std::to_wstring(match[1].length());
        WriteProgress("Found padding: " + StringConverter::to_string(n), verbose);
        stem = std::regex_replace(stem, std::wregex(L"([#]{" + n + L"})"), L"(\\d{" + n + L"})");
    } else {
        return std::nullopt;
    }

    return std::wregex(
        std::filesystem::path((_input_path.parent_path() / stem).wstring() + _input_path.extension().wstring())
            .make_preferred()
            .wstring());
}

int ConvertSequence(const std::wstring &input, const std::wstring &output, int size, int threads, bool verbose) {
    std::string input__ = StringConverter::to_string(input);
    std::string output__ = StringConverter::to_string(output);

    // Convert input to a path
    std::filesystem::path input_path(input);
    input_path = input_path.make_preferred();
    std::wstring input_ = input_path.wstring();
    std::filesystem::path intput_parent_dir = input_path.parent_path();

    // Convert output to a path
    std::filesystem::path output_path(output);
    output_path = output_path.make_preferred();
    std::wstring output_ = output_path.wstring();
    std::filesystem::path output_parent_dir = output_path.parent_path();

    std::wstring output_extension = output_path.extension().wstring();
    if (output_extension.empty()) {
        WriteError("Output file extension is empty", output__, empty_string_);
        return 1;
    }

    // Verify that the parent paths exists
    if (!std::filesystem::exists(intput_parent_dir) || !std::filesystem::is_directory(intput_parent_dir)) {
        WriteError("Parent directory does not exist", output_parent_dir.string(), empty_string_);
        return 1;
    }
    if (!std::filesystem::exists(output_parent_dir) || !std::filesystem::is_directory(output_parent_dir)) {
        WriteError("Parent directory does not exist", output_parent_dir.string(), empty_string_);
        return 1;
    }

    // Create cache
    auto image_cache = CreateCache();

    std::wstring file_name = input_path.filename();
    auto file_name_re = ConvertInputToRegex(file_name, verbose);

    if (!file_name_re) {
        WriteError("Does not seem like a file sequence. Try using ConvertImage instead.", input__, empty_string_);
        return 1;
    }

    // Iterate through the parent directory and find all matching files
    WriteProgress("Searching for matching files...", verbose);
    std::vector<std::wstring> inputs;
    for (const auto &entry : std::filesystem::directory_iterator(intput_parent_dir)) {
        std::wstring entry_name = entry.path().filename();
        if (!std::filesystem::is_regular_file(entry)) {
            continue;
        }
        if (std::regex_match(entry_name, *file_name_re)) {
            std::filesystem::path _path = entry.path();
            _path = _path.make_preferred();

            inputs.push_back(_path.wstring());
        }
    }

    if (inputs.empty()) {
        WriteError("Could not find file sequence items", input__, empty_string_);
        return 1;
    } else {
        WriteProgress("    Found " + std::to_string(inputs.size()) + " items", verbose);
    }

    std::wstring output_base_name = output_path.stem().wstring();
    output_base_name = std::regex_replace(output_base_name, std::wregex(L"[-_\\.\\s]*$"), L"");

    // Lambda function for processing a range of images
    auto process_images = [&](int start, int end) {
        for (int index = start; index < end; ++index) {
            const auto &i = inputs[index];
            std::wstring _output =
                output_parent_dir / (output_base_name + L"." + std::to_wstring(index) + output_extension);

            // Lock I/O operations if they're shared across threads
            WriteProgress("Processing image " + std::to_string(index + 1) + " of " + std::to_string(inputs.size()),
                          verbose);

            try {
                if (!CreateLockFile(i)) {
                    WriteError("Another process is already working on this file. Exiting...", StringConverter::to_string(i), empty_string_);
                    continue;  // Skip this file or handle error appropriately
                }

                int r = ConvertImage(i, _output, size, 1, false);  // two threads

                WriteProgress("Output: " + StringConverter::to_string(_output), verbose);

                RemoveLockFile(i);

                if (r != 0) {
                    WriteError("Error converting image", StringConverter::to_string(i), empty_string_);
                }
            } catch (const std::exception &e) {
                WriteError("Error converting image", StringConverter::to_string(i), std::string(e.what()));

                RemoveLockFile(i);
            }
        }
    };

    // Adjust number of threads based on inputs size and threads argument
    if (threads == 0) {
        threads = std::thread::hardware_concurrency();
    }
    int actual_threads = std::min(static_cast<size_t>(threads), inputs.size());
    std::vector<std::thread> workers;

    int inputs_per_thread = inputs.size() / actual_threads;
    int start = 0;

    for (int t = 0; t < actual_threads; ++t) {
        int end = start + inputs_per_thread + ((t < inputs.size() % actual_threads) ? 1 : 0);  // Handle remainder
        workers.emplace_back(std::thread(process_images, start, end));
        start = end;
    }

    // Join threads
    for (auto &worker : workers) {
        if (worker.joinable()) {
            worker.join();
        }
    }

    WriteProgress("Finished processing " + std::to_string(inputs.size()) + " items.", verbose);

    return 0;
}

int wmain(int argc, wchar_t *argv[]) {
    std::wstring input;
    std::string input_;
    std::wstring output;
    std::string output_;
    int size;
    int threads;
    bool verbose = false;

    std::locale::global(std::locale(""));
    std::cout.imbue(std::locale());
    std::cerr.imbue(std::locale());

    // Parse command line arguments
    CommandLineParser parser({
        {L"input", {{L"--input", L"-i"}, L"Source input image path", std::nullopt, true, true}},
        {L"output", {{L"--output", L"-o"}, L"Output image path", std::nullopt, true, true}},
        {L"size",
         {{L"--size", L"-s"},
          L"Output image size the longer edge should fit into. Use 0 to retain ",
          std::make_optional(L"0"),
          true,
          false}},
        {L"threads", {{L"--threads", L"-t"}, L"Number of threads to use", std::make_optional(L"0"), true, false}},
        {L"verbose", {{L"--verbose", L"-v"}, L"Show verbose information", std::make_optional(L"0"), true, false}},
    });

    try {
        parser.parse(argc, argv);
    } catch (const std::exception &e) {
        WriteError("Could not parse arguments", "-", std::string(e.what()));
        parser.showHelp();
        return 1;
    }

    if (argc <= 1) {
        parser.showHelp();
        return 0;
    }
    if (parser.has(L"input")) {
        input = parser.get<std::wstring>(L"input");
        input_ = StringConverter::to_string(input);
    }
    if (parser.has(L"output")) {
        output = parser.get<std::wstring>(L"output");
        output_ = StringConverter::to_string(output);
    }
    if (parser.has(L"size")) {
        size = parser.get<int>(L"size");
    }
    if (parser.has(L"threads")) {
        threads = parser.get<int>(L"threads");
        attribute("threads", threads);
    }
    if (parser.has(L"verbose")) {
        verbose = parser.get<bool>(L"verbose");
    }

    WriteProgress("Input image: " + input_, verbose);
    WriteProgress("Output image: " + output_, verbose);
    WriteProgress("Output size: " + std::to_string(size), verbose);
    WriteProgress("Number of threads: " + std::to_string(threads), verbose);

    auto image_cache = CreateCache();

    int r;
    try {
        if (!CreateLockFile(input)) {
            WriteError("Another process is already working on this file. Exiting...", input_, empty_string_);
            return 1;
        };
        r = ConvertImage(input, output, size, threads, verbose);
    } catch (const std::exception &e) {
        WriteError("Error making thumbnail", input_, std::string(e.what()));
        r = 1;
    }
    RemoveLockFile(input);
    return r;
}

#ifdef _PYBIND_MODULE
PYBIND11_MODULE(_PYBIND_MODULE, m) {
    m.doc() = "OpenImageIO image utility modules";
    m.def("convert_image", &ConvertImage, py::arg("input"), py::arg("output"), py::arg("size") = 0,
          py::arg("threads") = 0, py::arg("verbose") = false, py::return_value_policy::copy,
          py::call_guard<py::gil_scoped_release>(), "Converts an input image to an output image with a given size.");
    m.def("convert_sequence", &ConvertSequence, py::arg("input"), py::arg("output"), py::arg("size") = 0,
          py::arg("threads") = 0, py::arg("verbose") = false, py::return_value_policy::copy,
          py::call_guard<py::gil_scoped_release>(), "Converts input images to output images with a given size.");
}
#endif  // _PYBIND_MODULE
