#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <iostream> 
#include <filesystem>
#include <string>
#include <windows.h>
#include "dist.h"


#ifdef NO_CONSOLE
    #pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:wmainCRTStartup")
#endif


int wmain(int argc, wchar_t* argv[]) {
    std::filesystem::path root_dir;
    try {
        root_dir = std::filesystem::path(_wgetenv(Dist::ROOT_ENV_VAR.c_str()));
    } catch (std::exception& e) {
        MessageBoxW(NULL, (L"Failed to get " + Dist::ROOT_ENV_VAR + L" environment variable").c_str(), L"Error", MB_OK | MB_ICONERROR);
        std::wcerr << L"Failed to get " << Dist::ROOT_ENV_VAR << "environment variable: " << e.what() << L"\n";
        return 1;
    } 

    std::filesystem::path zip = L"python" + std::to_wstring(PY_MAJOR_VERSION) + std::to_wstring(PY_MINOR_VERSION) + L".zip";

    #if (PY_VERSION_HEX >= 0x03080000) // Python 3.8+

        PyStatus status;
        PyConfig config;

        // Initialize Python configuration in isolated mode
        PyConfig_InitIsolatedConfig(&config);

        config.optimization_level = 2;
        config.interactive = 0;
        config.use_environment = 0;
        config.user_site_directory = 0;
        config.install_signal_handlers = 1;

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

        status = PyConfig_SetString(&config, &config.run_command, Dist::PY_EXEC_SCRIPT.c_str());
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

        PyConfig_Clear(&config);
        int r = Py_RunMain();
        if (r != 0) {
            MessageBoxW(NULL, (L"Python encountered an error executing bookmarks\n"), L"Error", MB_OK | MB_ICONERROR);
            return r;
        }
    #else
        MessageBoxW(NULL, L"Python 3.8+ is required.", L"Error", MB_OK | MB_ICONERROR);
        return 1;
    #endif

    return 0;
}