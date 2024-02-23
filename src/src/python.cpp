#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "env.h"


int wmain(int argc, wchar_t* argv[]) {
    std::wcout << L"Bookmarks Python Interpreter" << std::endl;

    std::unordered_map<std::string, std::filesystem::path> paths = InitializeEnvironment(true);
    if (paths.empty()) {
        return -1;
    }

    std::filesystem::path root_dir = paths["root_dir"];
    std::filesystem::path zip = L"python" + std::to_wstring(PY_MAJOR_VERSION) + std::to_wstring(PY_MINOR_VERSION) + L".zip";

    #if (PY_VERSION_HEX >= 0x03080000) // Python 3.8+

        PyStatus status;
        PyConfig config;

        // Initialize Python configuration in isolated mode
        PyConfig_InitIsolatedConfig(&config);

        config.optimization_level = 0;
        config.interactive = 1;
        config.use_environment = 0;
        config.user_site_directory = 0;
        config.install_signal_handlers = 1;
        config.quiet = 1;

        // Home
        status = PyConfig_SetString(&config, &config.home, (root_dir / Dist::BIN_DIR).wstring().c_str());
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }

        // Module search paths
        config.module_search_paths_set = 1;
        status = PyWideStringList_Append(&config.module_search_paths, (root_dir / Dist::PRIVATE_DIR).wstring().c_str());
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }
        status = PyWideStringList_Append(&config.module_search_paths, (root_dir / Dist::SHARED_DIR).wstring().c_str());
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }
        status = PyWideStringList_Append(&config.module_search_paths, (root_dir / Dist::BIN_DIR).wstring().c_str());
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }
        status = PyWideStringList_Append(&config.module_search_paths, (root_dir / Dist::BIN_DIR / zip).wstring().c_str());
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }

        status = PyConfig_SetString(&config, &config.prefix, root_dir.wstring().c_str());
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }
        status = PyConfig_SetString(&config, &config.base_prefix, root_dir.wstring().c_str());
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }


        // argc and argv
        status = PyConfig_SetArgv(&config, argc, argv);
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }

        // Platform-specific directories
        status = PyConfig_SetString(&config, &config.platlibdir, (root_dir / Dist::PRIVATE_DIR).wstring().c_str());
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }

        // Initialize Python
        status = Py_InitializeFromConfig(&config);
        if (PyStatus_Exception(status)) {
            Py_ExitStatusException(status);
            return 1;
        }
        
        // Let's check for either an -m or -c flag and run Py_RunMain() if neither are found

        PyConfig_Clear(&config);
        return Py_Main(argc, argv);
    #else
        MessageBoxW(NULL, L"Python 3.8+ is required.", L"Error", MB_OK | MB_ICONERROR);
        return 1;
    #endif

    return 0;
}