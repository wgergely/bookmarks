#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "env.h"

#ifdef NO_CONSOLE
#pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:wmainCRTStartup")
#endif

int wmain(int argc, wchar_t *argv[]) {
    Dist::Paths paths = InitializeEnvironment(true);
    // Chek that paths.root exists
    if (!std::filesystem::exists(paths.root) || !std::filesystem::is_directory(paths.root)) {
        MessageBoxW(NULL, (L"Could not find " + paths.root.wstring()).c_str(), L"Error", MB_OK | MB_ICONERROR);
    }

#if (PY_VERSION_HEX >= 0x03080000)  // Python 3.8+

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
    status = PyConfig_SetString(&config, &config.home, paths.bin.wstring().c_str());
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
        return 1;
    }

    // Module search paths
    config.module_search_paths_set = 1;
    status = PyWideStringList_Append(&config.module_search_paths, paths.core.wstring().c_str());
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
        return 1;
    }
    status = PyWideStringList_Append(&config.module_search_paths, paths.shared.wstring().c_str());
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
        return 1;
    }
    status = PyWideStringList_Append(&config.module_search_paths, paths.bin.wstring().c_str());
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
        return 1;
    }
    status = PyWideStringList_Append(&config.module_search_paths, paths.py_zip.wstring().c_str());
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
    status = PyConfig_SetString(&config, &config.platlibdir, paths.internal.wstring().c_str());
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