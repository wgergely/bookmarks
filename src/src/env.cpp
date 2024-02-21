#include "env.h"

std::wstring ConvertToWideString(const std::string& input) {
    if (input.empty()) return std::wstring();
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, &input[0], (int)input.size(), NULL, 0);
    std::wstring wstrTo(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, &input[0], (int)input.size(), &wstrTo[0], size_needed);
    return wstrTo;
}


std::unordered_map<std::string, std::filesystem::path> InitializeEnvironment() {
    std::unordered_map<std::string, std::filesystem::path> paths;

    if (!_WIN32) {
        std::wcerr << L"Error: Requires a Windows operating system\n";
        return {};
    }

    wchar_t exe_path[MAX_PATH];
    if (GetModuleFileNameW(NULL, exe_path, MAX_PATH) == 0) {
        #ifndef NO_CONSOLE
        MessageBoxW(NULL, L"Failed to get module file name.", L"Error", MB_ICONERROR | MB_OK);
        #endif
        std::wcerr << L"Error: Failed to get module file name (" << GetLastError() << L").\n";
        return {};
    }

    std::filesystem::path exe_full_path(exe_path);
    std::filesystem::path root_dir = exe_full_path.parent_path();

    // Define directories
    std::filesystem::path shared_dir = root_dir / Dist::SHARED_DIR;
    std::filesystem::path private_dir = root_dir / Dist::PRIVATE_DIR;
    std::filesystem::path bin_dir = root_dir / Dist::BIN_DIR;
    std::filesystem::path plugins_dir = root_dir / Dist::PLUGINS_DIR;
    std::filesystem::path py_module_dir = root_dir / Dist::SHARED_DIR / Dist::PY_MODULE_DIR;
    std::filesystem::path py_startup = root_dir / Dist::BIN_DIR / Dist::PY_STARTUP;
    std::filesystem::path py_exe = root_dir / Dist::BIN_DIR / Dist::PY_EXE;

    // Check if required directories exist
    for (const auto& dir : {plugins_dir, shared_dir, private_dir, bin_dir, py_module_dir}) {
        if (!std::filesystem::exists(dir) || !std::filesystem::is_directory(dir)) {
            #ifndef NO_CONSOLE
            MessageBoxW(NULL, (L"A required directory was not found:\n" + dir.wstring()).c_str(), L"Error", MB_ICONERROR | MB_OK);
            #endif
            std::wcerr << L"Error: A required directory was not found:\n" << dir << std::endl;
            return {};
        }
    }
    // Check if required files exist
    for (const auto& file : {py_startup, py_exe}) {
        if (!std::filesystem::exists(file) || !std::filesystem::is_regular_file(file)) {
            #ifndef NO_CONSOLE
            MessageBoxW(NULL, (L"A required file was not found:\n" + file.wstring()).c_str(), L"Error", MB_ICONERROR | MB_OK);
            #endif
            std::wcerr << L"Error: A required file was not found:\n" << file << std::endl;
            return {};
        }
    }

    // Set Python environment variables
    SetEnvironmentVariableW(L"PYTHONHOME", root_dir.c_str());
    SetEnvironmentVariableW(L"PYTHONPATH", (private_dir.wstring() + L";" + shared_dir.wstring()).c_str());
    SetEnvironmentVariableW(L"PYTHONSTARTUP", py_startup.wstring().c_str());    

    // Set PATH environment variable
    std::wstring new_path = (
        root_dir.wstring() + L";" + 
        plugins_dir.wstring() + L";" + 
        bin_dir.wstring() + L";" + 
        private_dir.wstring() + L";" +
        shared_dir.wstring() + L";"
    );
    wchar_t* current_path = nullptr;
    size_t size;
    _wdupenv_s(&current_path, &size, L"PATH");
    if (current_path) {
        new_path += current_path;
        free(current_path);
    }
    SetEnvironmentVariableW(L"PATH", new_path.c_str());

    // Add DLL directories
    // SetDllDirecotory seems to be required for locating files in the bin directory
    // as AddDllDirectory does not seem to affect the search path (?)s
    SetDllDirectoryW(bin_dir.wstring().c_str());

    AddDllDirectory(bin_dir.wstring().c_str());
    AddDllDirectory(private_dir.wstring().c_str());
    AddDllDirectory(shared_dir.wstring().c_str());
    AddDllDirectory(plugins_dir.wstring().c_str());

    // Set Bookmarks environment variables
    SetEnvironmentVariableW(L"BOOKMARKS_ROOT", root_dir.wstring().c_str());
    SetEnvironmentVariableW(L"BOOKMARKS_BIN_DIR", bin_dir.wstring().c_str());
    #ifdef Bookmarks_VERSION
    std::wstring version = ConvertToWideString(Bookmarks_VERSION);
    SetEnvironmentVariableW(L"Bookmarks_VERSION", version.c_str());
    #else
    std::wstring version = L"0.0.0";
    SetEnvironmentVariableW(L"Bookmarks_VERSION", version.c_str());
    #endif

    paths["root_dir"] = root_dir;
    paths["shared_dir"] = shared_dir;
    paths["private_dir"] = private_dir;
    paths["bin_dir"] = bin_dir;
    paths["py_module_dir"] = py_module_dir;
    paths["py_startup"] = py_startup;
    paths["py_exe"] = py_exe;

    #ifndef NO_CONSOLE
    std::wcout << L"PYTHONHOME=" << root_dir.wstring() << std::endl;
    std::wcout << L"PYTHONPATH=" << private_dir.wstring() << L";" << shared_dir.wstring() << std::endl;
    std::wcout << L"PYTHONSTARTUP=" << py_startup.wstring() << std::endl;
    std::wcout << L"BOOKMARKS_ROOT=" << root_dir.wstring() << std::endl;
    std::wcout << L"BOOKMARKS_BIN_DIR=" << bin_dir.wstring() << std::endl;
    std::wcout << L"BOOKMARKS_VERSION=" << version << std::endl;
    #endif

    return paths;
}