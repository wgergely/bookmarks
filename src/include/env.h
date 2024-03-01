#ifndef ENV_H
#define ENV_H

#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif  // _WIN32
#include <filesystem>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>

#include "dist.h"

Dist::Paths InitializeEnvironment(bool use_grandparent = false);

int LaunchProcess(int argc, wchar_t *argv[], std::filesystem::path exe_path);

#endif  // ENV_H