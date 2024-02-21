#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "env.h"


#ifdef NO_CONSOLE
    #pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:wmainCRTStartup")
#endif


std::string wide_to_utf8(const std::wstring& wstr) {
    if (wstr.empty()) return std::string();

    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &wstr[0], (int)wstr.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &wstr[0], (int)wstr.size(), &strTo[0], size_needed, NULL, NULL);

    return strTo;
}


int wmain(int argc, wchar_t* argv[]) {
    auto paths = InitializeEnvironment();
    if (paths.empty()) {
        return -1; // Initialization failed
    }

    // Initialize Python
    Py_Initialize();

    if (!Py_IsInitialized()) {
        std::wcerr << L"Failed to initialize Python.\n";
        return 1;
    }

    // Set Python DLL directories (for Python 3.8+)
    if (PY_VERSION_HEX >= 0x03080000) {
        PyObject* path_hook = PySys_GetObject("path_hooks");
        if (!path_hook) {
            std::wcerr << L"Failed to get Python path_hooks.\n";
            Py_Finalize();
            return 1;
        }

        std::filesystem::path root_dir = paths["root"];
        std::filesystem::path bin_dir = paths["bin"];
        std::filesystem::path private_dir = paths["private"];

        std::wstring py_dll_cmd = (
            L"import os;"
            L"os.add_dll_directory('" + root_dir.wstring() + L"');"
            L"os.add_dll_directory('" + bin_dir.wstring() + L"');"
            L"os.add_dll_directory('" + private_dir.wstring() + L"');"
        );

        if (PyRun_SimpleString(wide_to_utf8(py_dll_cmd).c_str()) != 0) {
            std::wcerr << L"Failed to add DLL directories.\n";
            Py_Finalize();
            return 1;
        }
    }

    // Execute main script
    std::wstring py_exec_cmd = L"import bookmarks;bookmarks.exec_()\n";
    if (PyRun_SimpleString(wide_to_utf8(py_exec_cmd).c_str()) != 0) {
        std::wcerr << L"Python encountered an error executing the bookmarks script.\n";
    }

    Py_Finalize();
    return 0;
}
