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


// Make sure the console is hidden in Release
#if (defined NDEBUG && defined _WIN32)
//#pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:mainCRTStartup")
#endif


static std::string LIB_DIR = std::string("python37.zip");	// The standard python modules
static std::string SHARED_DIR = std::string("shared");		// 3rd party dependencies to make available for DCCs
static std::string PRIVATE_DIR = std::string("private");	// PySide2 and Alembic are private as DCCs (like Maya) might already have these
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
	//throw std::runtime_error(std::string("A directory was not found:\n") + path);
}


std::string _path(const std::string r, const std::string p)
{
	return r + std::string("\\") + p;
}

int main(int argc, char** argv) {
	
	// Get the program name using GetModuleFileNameW
	char _root[MAX_PATH + 1];

	if (_WIN32)
		GetModuleFileNameA(NULL, _root, MAX_PATH);
	else
		throw std::runtime_error("Only Windows is implemented.");

	std::string root = _root;
	root = root.substr(0, root.find_last_of("/\\"));
	
	// Verify integrity
	std::string _lib_dir = _path(root, LIB_DIR);
	std::string _shared_dir = _path(root, SHARED_DIR);
	std::string _priv_dir = _path(root, PRIVATE_DIR);
	std::string _bin_dir = _path(root, BIN_DIR);

	std::string _modules = root + ";" + _lib_dir + ";" + _shared_dir + ";" + _priv_dir;

	if (_dir_missing(_shared_dir) || _dir_missing(_priv_dir)) {
		exit(1);
	}

	// Add dirs to PATH
	std::stringstream string_stream;
	string_stream << root << ";";
	string_stream << _modules << ";";
	string_stream << getenv("PATH");
	string_stream << '\0';
	std::string env = string_stream.str();

	// Set PATH
	int result = _setenv("PATH", env.c_str(), 1);


	// Environment setup
	_setenv("PYTHONNOUSERSITE", "", 1);
	_setenv("PYTHONHOME", _lib_dir.c_str(), 1);
	_setenv("PYTHONPATH", _modules.c_str(), 1);
	
	size_t argv_st = strlen(argv[0]);
	Py_SetProgramName(Py_DecodeLocale(argv[0], &argv_st));
	
	size_t home_st = strlen(_lib_dir.c_str());
	Py_SetPythonHome(Py_DecodeLocale(_lib_dir.c_str(), &home_st));

	size_t mod_st = strlen(_modules.c_str());
	Py_SetPath(Py_DecodeLocale(_modules.c_str(), &mod_st));

	Py_InitializeEx(0);

	printf("Executable: %s\n", argv[0]);
	printf("Root Directory: %s\n", root.c_str());
	printf("PATH: %s\n", env.c_str());
	
	int r = PyRun_SimpleString(
		"import bookmarks; bookmarks.exec_()"
	);
	if (r != 0)
		printf("Python encountered an error.");
		Py_FinalizeEx();
		exit(1);
		
	exit(0);
}