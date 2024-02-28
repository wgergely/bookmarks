#include "env.h"

#ifdef NO_CONSOLE
#pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:wmainCRTStartup")
#endif

int wmain(int argc, wchar_t *argv[]) {
  Dist::Paths paths = InitializeEnvironment(false);

  try {
    return LaunchProcess(argc, argv, paths.py_launcher_exe);
  } catch (std::exception &e) {
    MessageBoxA(NULL, e.what(), "Error", MB_ICONERROR);
    std::wcerr << L"Error: " << e.what() << L"\n";
    return 1;
  }

  return 0;
}