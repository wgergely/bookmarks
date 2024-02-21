#include "env.h"

// Macro to convert a define value to a wide string
#define WIDEN2(x) L##x
#define WIDEN(x) WIDEN2(x)


int wmain(int argc, wchar_t* argv[]) {
    std::unordered_map<std::string, std::filesystem::path> paths = InitializeEnvironment();
    if (paths.empty()) {
        return -1; // Initialization failed
    }

    // Prepare the command line for CreateProcessW
    std::filesystem::path py_exe = paths["py_exe"];
    std::wstring cmdLine = py_exe.wstring();
    for (int i = 1; i < argc; ++i) {
        cmdLine += L" ";
        cmdLine += argv[i];
    }

    // Launch the executable using wide-character version
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcessW(NULL, &cmdLine[0], NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        std::wcerr << L"CreateProcess failed (" << GetLastError() << L").\n";
        return 1;
    }

    // Wait until child process exits.
    WaitForSingleObject(pi.hProcess, INFINITE);

    // Close process and thread handles.
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return 0;

}
