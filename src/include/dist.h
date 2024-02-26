#ifndef DIST_H
#define DIST_H

namespace Dist
{
    // Directory constants
    const std::filesystem::path BIN_DIR = "bin";
    const std::filesystem::path CORE_MODULES_DIR = "core";
    const std::filesystem::path INTERNAL_MODULES_DIR = "internal";
    const std::filesystem::path SHARED_MODULES_DIR = "shared";

    // File & Executable constants
    const std::filesystem::path PY_STARTUP = ".pythonstartup";
    const std::filesystem::path PY_EXE = "python.exe";
    const std::filesystem::path PY_LAUNCHER_EXE = "py-launcher.exe";
#if defined(PY_MAJOR_VERSION) && defined(PY_MINOR_VERSION)
    const std::filesystem::path PY_ZIP = L"python" + std::to_wstring(PY_MAJOR_VERSION) + std::to_wstring(PY_MINOR_VERSION) + L".zip";
#endif

    // Environment variables
    const std::wstring ROOT_ENV_VAR = L"Bookmarks_ROOT";
    const std::wstring PY_EXEC_SCRIPT = L"import bookmarks;bookmarks.exec()";

    struct Paths
    {
        std::filesystem::path exe;
        std::filesystem::path root;
        std::filesystem::path bin;
        std::filesystem::path core;
        std::filesystem::path internal;
        std::filesystem::path shared;

        std::filesystem::path py_startup;
        std::filesystem::path py_exe;
        std::filesystem::path py_launcher_exe;
#if defined(PY_MAJOR_VERSION) && defined(PY_MINOR_VERSION)
        std::filesystem::path py_zip;
#endif
    };
}

#endif // DIST_H
