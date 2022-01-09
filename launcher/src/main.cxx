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
#include <windows.h>
#include <shlwapi.h>


// Make the console hidden
//#pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:mainCRTStartup")


static std::string SHARED_DIR = std::string("shared");		// 3rd party dependencies to make available for DCCs
static std::string CORE_DIR = std::string("core");	// PySide2 and Alembic are private as DCCs (like Maya) might already have these
static std::string BIN_DIR = std::string("bin");			// All the *.dlls required the Python modules


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
	printf("A required directory was not found:\n>>   %s", path.c_str());
	return true;
}


std::string _path(const std::string r, const std::string p)
{
	return r + std::string("\\") + p;
}

int main(int argc, char** argv) {
		if (!_WIN32) {
		fprintf(stderr, "Reqauires a Windows operating system");
		exit(1);
	}
	
	// Get the program name using GetModuleFileNameW
	char _root[MAX_PATH + 1];
	GetModuleFileNameA(NULL, _root, MAX_PATH);
		
	std::string root = _root;
	root = root.substr(0, root.find_last_of("/\\"));
	
	// PYTHONHOME
	_setenv("PYTHONNOUSERSITE", "", 1);
	_setenv("PYTHONHOME", root.c_str(), 1);

	// PYTHONPATH
	std::string _shared_dir = _path(root, SHARED_DIR);
	std::string _core_dir = _path(root, CORE_DIR);
	std::string _modules = _shared_dir + ";" + _core_dir;
	_setenv("PYTHONPATH", _modules.c_str(), 1);

	if (_dir_missing(_shared_dir) || _dir_missing(_core_dir)) {
		fprintf(stderr, "A subdirectory is missing.");
		exit(1);
	}

	// PATH
	std::string _bin_dir = _path(root, BIN_DIR);
	std::stringstream string_stream;
	string_stream << root << ";";
	string_stream << _bin_dir << ";";
	string_stream << getenv("PATH");
	string_stream << '\0';
	std::string env = string_stream.str();
	_setenv("PATH", env.c_str(), 1);

	size_t argv_st = strlen(argv[0]);
	wchar_t *program = Py_DecodeLocale(argv[0], &argv_st);
	if (program == NULL) {
		fprintf(stderr, "Fatal error: cannot decode argv[0]\n");
		exit(1);
	}

	Py_SetProgramName(program);
	
	Py_InitializeEx(0);

	int result = PyRun_SimpleString(
		"import bookmarks; bookmarks.exec_()"
	);
	if (result != 0) {
		fprintf(stderr, "Python encountered an error.\n");
	}
	if (Py_FinalizeEx() < 0) {
		exit(120);
	}
	PyMem_RawFree(program);	
	exit(0);
}