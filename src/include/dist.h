#ifndef DIST_H
#define DIST_H

namespace Dist {
    const std::filesystem::path SHARED_DIR = "shared";
    const std::filesystem::path PRIVATE_DIR = "private";
    const std::filesystem::path BIN_DIR = "bin";
    const std::filesystem::path PLUGINS_DIR = "bin";
    const std::filesystem::path PY_STARTUP = ".pythonstartup";
    const std::filesystem::path PY_MODULE_DIR = "bookmarks";
    const std::filesystem::path PY_EXE = "python.exe";
    const std::filesystem::path PY_LAUNCHER_EXE = "py-launcher.exe";
    const std::wstring ROOT_ENV_VAR = L"Bookmarks_ROOT";
    const std::wstring PY_EXEC_SCRIPT = L"import bookmarks;bookmarks.exec()";
}

#endif // DIST_H
