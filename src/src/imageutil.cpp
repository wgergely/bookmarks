#include <string>
#include <iostream>
#include <cstdlib>
#include <limits>

#include <imageutil.h>

int main(int argc, char* argv[]) {
    if (argc < 4 || argc > 5) {
        std::cerr << "Error: expected 3 or 4 arguments" << std::endl;
        std::cerr << "Usage: " << argv[0] << " input_image output_image size [-d]" << std::endl;
        return 1;
    }

    std::string input_image = argv[1];
    std::string output_image = argv[2];
    int size = std::atoi(argv[3]);

    if (input_image == output_image) {
        std::cerr << "Error: input_image and output_image cannot be the same" << std::endl;
        return 1;
    }

    bool debug = false;
    if (argc == 5) {
        std::string debug_arg = argv[4];
        if (debug_arg != "-d") {
            std::cerr << "Error: expected '-d' for debug mode\n";
            return 1;
        }
        debug = true;
    }

	bool r = convert_image(input_image, output_image, size, debug);
    if (!r) {
        std::cerr << "Could not convert image" << std::endl;
        return 1;
    }

	return 0;
}