#ifndef ENV_H
#define ENV_H

#include <iostream>
#include <windows.h>
#include <string>
#include <filesystem>
#include <unordered_map>

#include "dist.h"

std::unordered_map<std::string, std::filesystem::path> InitializeEnvironment(bool use_grandparent=false);
int LaunchProcess(int argc, wchar_t* argv[], std::filesystem::path exe_path);

#endif // ENV_H