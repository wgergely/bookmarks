#include "env.h"

std::wstring ConvertToWideString(const std::string &input)
{
  if (input.empty())
    return std::wstring();
  int size_needed =
      MultiByteToWideChar(CP_UTF8, 0, &input[0], (int)input.size(), NULL, 0);
  std::wstring wstrTo(size_needed, 0);
  MultiByteToWideChar(CP_UTF8, 0, &input[0], (int)input.size(), &wstrTo[0],
                      size_needed);
  return wstrTo;
}

Dist::Paths InitializeEnvironment(bool use_grandparent)
{
  if (!_WIN32)
  {
    std::wcerr << L"Error: Requires a Windows operating system\n";
    return {};
  }

  wchar_t exe_path[MAX_PATH];
  if (GetModuleFileNameW(NULL, exe_path, MAX_PATH) == 0)
  {
#ifndef NO_CONSOLE
    MessageBoxW(NULL,
                L"Failed to get module file name.",
                L"Error",
                MB_ICONERROR | MB_OK);
#endif
    std::wcerr << L"Error: Failed to get module file name (" << GetLastError()
               << L").\n";
    return {};
  }

  std::filesystem::path exe_full_path(exe_path);
  if (use_grandparent)
  {
    exe_full_path = exe_full_path.parent_path();
  }

  Dist::Paths paths;
  paths.exe = exe_full_path;
  paths.root = exe_full_path.parent_path();
  paths.bin = paths.root / Dist::BIN_DIR;
  paths.shared = paths.root / Dist::SHARED_MODULES_DIR;
  paths.internal = paths.root / Dist::INTERNAL_MODULES_DIR;
  paths.core = paths.root / Dist::CORE_MODULES_DIR;

#if defined(PY_MAJOR_VERSION) && defined(PY_MINOR_VERSION)
  paths.py_startup = paths.root / Dist::BIN_DIR / Dist::PY_STARTUP;
  paths.py_exe = paths.root / Dist::BIN_DIR / Dist::PY_EXE;
  paths.py_launcher_exe = paths.root / Dist::BIN_DIR / Dist::PY_LAUNCHER_EXE;
  paths.py_zip = paths.root / Dist::BIN_DIR / Dist::PY_ZIP;
#endif

  // Add/Set DLL directories
  SetDllDirectoryW(paths.bin.wstring().c_str());
  AddDllDirectory(paths.bin.wstring().c_str());
  AddDllDirectory(paths.core.wstring().c_str());
  AddDllDirectory(paths.internal.wstring().c_str());
  AddDllDirectory(paths.shared.wstring().c_str());

  // Check if required directories exist
  for (const auto &dir :
       {paths.core, paths.shared, paths.internal, paths.bin})
  {
    if (!std::filesystem::exists(dir) || !std::filesystem::is_directory(dir))
    {
#ifndef NO_CONSOLE
      MessageBoxW(
          NULL,
          (L"A required directory was not found:\n" + dir.wstring()).c_str(),
          L"Error", MB_ICONERROR | MB_OK);
#endif
      std::wcerr << L"Error: A required directory was not found:\n"
                 << dir << std::endl;
      return {};
    }
  }
  // Check if required files exist
  for (const auto &file :
       {paths.py_startup, paths.py_exe, paths.py_launcher_exe})
  {
    if (!std::filesystem::exists(file) ||
        !std::filesystem::is_regular_file(file))
    {
#ifndef NO_CONSOLE
      MessageBoxW(
          NULL, (L"A required file was not found:\n" + file.wstring()).c_str(),
          L"Error", MB_ICONERROR | MB_OK);
#endif
      std::wcerr << L"Error: A required file was not found:\n"
                 << file << std::endl;
      return {};
    }
  }

  // Set Python environment variables
  SetEnvironmentVariableW(L"PYTHONHOME", paths.bin.wstring().c_str());
  SetEnvironmentVariableW(L"PYTHONPATH", (paths.core.wstring() + L";" +
                                          paths.internal.wstring() + L";" +
                                          paths.shared.wstring())
                                             .c_str());
  SetEnvironmentVariableW(L"PYTHONSTARTUP", paths.py_startup.wstring().c_str());

  // Set PATH environment variable
  std::wstring _n_path =
      (paths.root.wstring() + L";" +
       paths.bin.wstring() + L";" +
       paths.internal.wstring() + L";" +
       paths.shared.wstring() + L";" +
       paths.core.wstring() + L";");
  wchar_t *_c_path = nullptr;
  size_t size;
  _wdupenv_s(&_c_path, &size, L"PATH");
  if (_c_path)
  {
    _n_path += _c_path;
    free(_c_path);
  }
  SetEnvironmentVariableW(L"PATH", _n_path.c_str());

  // Environment variables
  SetEnvironmentVariableW(L"Bookmarks_ROOT", paths.root.wstring().c_str());
#ifdef Bookmarks_VERSION
  std::wstring version = ConvertToWideString(Bookmarks_VERSION);
  SetEnvironmentVariableW(L"Bookmarks_VERSION", version.c_str());
#else
  std::wstring version = L"0.0.0";
  SetEnvironmentVariableW(L"Bookmarks_VERSION", version.c_str());
#endif

#ifndef NO_CONSOLE
  std::wcout << L"Bookmarks_ROOT=" << paths.root.wstring() << std::endl;
  std::wcout << L"Bookmarks_VERSION=" << version << std::endl;
#endif

  return paths;
}

int LaunchProcess(int argc, wchar_t *argv[], std::filesystem::path exe_path)
{
  if (exe_path.empty())
  {
    MessageBoxW(NULL, L"Error: Empty executable path.", L"Error",
                MB_ICONERROR | MB_OK);
    std::wcerr << L"Error: Empty executable path.\n";
    return 1;
  }
  if (!std::filesystem::exists(exe_path) ||
      !std::filesystem::is_regular_file(exe_path))
  {
    MessageBoxW(NULL,
                (L"Error: " + exe_path.wstring() + L" not found.").c_str(),
                L"Error", MB_ICONERROR | MB_OK);
    std::wcerr << L"Error: " << exe_path.wstring() << " not found.\n";
    return 1;
  }

  // Prepare the command line for CreateProcessW
  std::wstring cmd = exe_path.wstring();
  for (int i = 1; i < argc; ++i)
  {
    cmd += L" ";
    cmd += argv[i];
  }

  // Launch the executable using wide-character version
  STARTUPINFOW si;
  PROCESS_INFORMATION pi;
  ZeroMemory(&si, sizeof(si));
  si.cb = sizeof(si);
  ZeroMemory(&pi, sizeof(pi));

  if (!CreateProcessW(NULL, &cmd[0], NULL, NULL, FALSE, 0, NULL, NULL, &si,
                      &pi))
  {
    MessageBoxW(
        NULL,
        (L"CreateProcess failed (" + std::to_wstring(GetLastError()) + L").")
            .c_str(),
        L"Error", MB_ICONERROR | MB_OK);
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