/*
The Bookmarks application will set up the environment so that bookmarks can be run
as a standalone application package.

<Python.h> will include the following standard headers:
<stdio.h>, <string.h>, <errno.h>, <limits.h>, <astring_streamert.h> and <stdlib.h>

*/
#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <config.h>

#include <sstream>
#include <algorithm>
#include <windows.h>
#include <shlwapi.h>


#ifdef NO_CONSOLE
	#pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:mainCRTStartup")
#endif

static std::string SHARED_DIR = std::string("shared");		// 3rd party dependencies to make available for DCCs
static std::string CORE_DIR = std::string("core");			// PySide2 and Alembic are private as DCCs (like Maya) might already have these
static std::string BIN_DIR = std::string("bin");			// All the *.dlls required by the python modules
static std::string BIN = std::string("Bookmarks.exe");		// Main executable


int _setenv(const char *name, const char *value, int overwrite)
/* The <stdlib.h> does not declare setenv, but uses _putenv/_putenv_s intead. */
{
	int errcode = 0;
	if (!overwrite) {
		size_t envsize = 0;
		errcode = getenv_s(&envsize, NULL, 0, name);
		if (errcode || envsize) return errcode;
	}
	return _putenv_s(name, value);
}


bool _check_dir(std::string path)
{
	struct stat st;
	if (stat(path.c_str(), &st) != 0)
		return true;
	if ((st.st_mode & S_IFDIR) == 0)
		return true;
	return false;
}


bool _dir_missing(std::string path)
{
	if (!_check_dir(path))
		return false;
	printf("A required directory was not found:\n>>   %s\n", path.c_str());
	return true;
}


std::string _fw_slash(const std::string s) {
	std::string r = s;
	std::replace(r.begin(), r.end(), '\\', '/');
	return r;
}

std::string _path(const std::string r, const std::string p)
{
	std::stringstream string_stream;
	string_stream << r << "/" << p << "\0";
	std::string result = string_stream.str();
	std::replace(result.begin(), result.end(), '\\', '/');
	return _fw_slash(result);
}

int main(int argc, char** argv) {
	if (!_WIN32) {
		fprintf(stderr, "Requires a Windows operating system\n");
		exit(1);
	}
	
	// Get the program name using GetModuleFileNameW
	char _root[MAX_PATH + 1];
	GetModuleFileNameA(NULL, _root, MAX_PATH);
		
	std::string root = _fw_slash(_root);
	root = root.substr(0, root.find_last_of("/"));

	// DIRECTORIES
	std::string _shared_dir = _path(root, SHARED_DIR);
	std::string _core_dir = _path(root, CORE_DIR);
	std::string _bin = _path(root, BIN);
	std::string _modules = _shared_dir + ";" + _core_dir;

	if (_dir_missing(_shared_dir) || _dir_missing(_core_dir)) {
		fprintf(stderr, "A subdirectory is missing.\n");
		exit(1);
	}

	// PATH
	std::string _bin_dir = _path(root, BIN_DIR);
	std::stringstream py_dll_directories;
	std::stringstream string_stream;

	string_stream << root << ";";
	string_stream << _bin_dir << ";";
	string_stream << getenv("PATH");
	string_stream << '\0';
	std::string env = string_stream.str();
	_setenv("PATH", env.c_str(), 1);

	PyStatus status;

	PyConfig config;
	PyConfig_InitPythonConfig(&config);
	config.isolated = 1;

	/* Set the program name before reading the configuration
	   (decode byte string from the locale encoding).

	   Implicitly preinitialize Python. */
	status = PyConfig_SetBytesArgv(&config, argc, argv);
	if (PyStatus_Exception(status)) {
		goto fail;
	}
	status = PyConfig_SetBytesString(&config, &config.home, root.c_str());
	status = PyConfig_SetBytesString(&config, &config.pythonpath_env, _modules.c_str());
	status = PyConfig_SetBytesString(&config, &config.executable, _bin.c_str());
	if (PyStatus_Exception(status)) {
		goto fail;
	}

	status = Py_InitializeFromConfig(&config);
	if (PyStatus_Exception(status)) {
		goto fail;
	}
	
	int result;

	if (PY_VERSION_HEX >= 0x03080000) {
		// Python version is 3.8 or newer
		py_dll_directories << "import os;";
		py_dll_directories << "os.add_dll_directory('" << root.c_str() << "');";
		py_dll_directories << "os.add_dll_directory('" << _bin_dir.c_str() << "');";
		py_dll_directories << "os.add_dll_directory('" << _core_dir.c_str() << "');";
		py_dll_directories << '\0';
		
		result = PyRun_SimpleString(py_dll_directories.str().c_str());
		if (result != 0) {
			fprintf(stderr, "Python encountered an error.\n");
		}
	} else {
		// For older versions, modify the PATH environment variable
		std::string newPath = getenv("PATH");
		newPath = root + ";" + _bin_dir + ";" + _core_dir + ";" + newPath;
		_setenv("PATH", newPath.c_str(), 1);
	}

	result = PyRun_SimpleString(py_dll_directories.str().c_str());
	if (result != 0) {
		fprintf(stderr, "Python encountered an error.\n");
	}

	// Let's call the main bookmarks launch script
	result = PyRun_SimpleString(
		"import bookmarks;bookmarks.exec_()"
	);
	if (result != 0) {
		fprintf(stderr, "Python encountered an error.\n");
	}

	PyConfig_Clear(&config);
	return 0;


	fail:
		PyConfig_Clear(&config);
		if (PyStatus_IsExit(status)) {
			return status.exitcode;
		}
		/* Display the error message and exit the process with
		   non-zero exit code */
		Py_ExitStatusException(status);
}