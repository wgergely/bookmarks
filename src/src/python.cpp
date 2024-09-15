#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "env.h"
#include "stringconverter.h"

int wmain(int argc, wchar_t *argv[])
{
    Dist::Paths paths = InitializeEnvironment(true);
#ifdef ADD_CORE_MODULE
    std::wcout << L"# Core module: " << paths.core.wstring() << std::endl;
#else
    std::wcout << L"# Core module not loaded" << std::endl;
#endif

#if (PY_VERSION_HEX < 0x03080000) // Python 3.8+
    MessageBoxW(NULL, L"Python 3.8+ is required.", L"Error", MB_OK | MB_ICONERROR);
    return 1;
#endif

    PyStatus status;
    PyConfig config;

// Initialize Python configuration in isolated mode
#ifdef ADD_CORE_MODULE
    PyConfig_InitIsolatedConfig(&config);
#else
    PyConfig_InitPythonConfig(&config);
#endif // ADD_CORE_MODULE

    config.optimization_level = 0;
    config.interactive = 1;
    config.user_site_directory = 0;
    config.safe_path = 1;
    config.use_environment = 0;

    config.install_signal_handlers = 1;
    // config.quiet = 1;

    // Home
    status = PyConfig_SetString(&config, &config.home, paths.bin.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }

    // Module search paths
    config.module_search_paths_set = 1;
#ifdef ADD_CORE_MODULE
    status = PyWideStringList_Append(&config.module_search_paths, paths.core.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }
#else
    const char *pythonpath_env = std::getenv("PYTHONPATH");
    if (pythonpath_env != nullptr)
    {
        std::wstring pythonpath_env_w = StringConverter::to_wstring(pythonpath_env ? pythonpath_env : "");
        if (pythonpath_env_w != L"")
        {
            std::vector<std::wstring> pythonpath_env_w_split;
            std::wstringstream ss(pythonpath_env_w);
            std::wstring item;

            while (std::getline(ss, item, L';'))
            {
                pythonpath_env_w_split.push_back(item);
            }

            for (const auto &path : pythonpath_env_w_split)
            {
                status = PyWideStringList_Append(&config.module_search_paths, path.c_str());
                if (PyStatus_Exception(status))
                {
                    Py_ExitStatusException(status);
                    return 1;
                }
            }
        }
    }
#endif // ADD_CORE_MODULE

    status = PyWideStringList_Append(&config.module_search_paths, paths.internal.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }
    status = PyWideStringList_Append(&config.module_search_paths, paths.shared.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }
    status = PyWideStringList_Append(&config.module_search_paths, paths.bin.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }
    status = PyWideStringList_Append(&config.module_search_paths, paths.py_zip.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }

    status = PyConfig_SetString(&config, &config.prefix, paths.root.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }
    status = PyConfig_SetString(&config, &config.base_prefix, paths.root.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }

    // argc and argv
    status = PyConfig_SetArgv(&config, argc, argv);
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }

    // Platform-specific directories
    status = PyConfig_SetString(&config, &config.platlibdir, paths.internal.wstring().c_str());
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }

    // Initialize Python
    status = Py_InitializeFromConfig(&config);
    if (PyStatus_Exception(status))
    {
        Py_ExitStatusException(status);
        return 1;
    }

    PyConfig_Clear(&config);
    return Py_Main(argc, argv);
}