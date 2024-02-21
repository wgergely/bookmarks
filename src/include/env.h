#ifndef ENV_H
#define ENV_H

#include <iostream>
#include <windows.h>
#include <string>
#include <filesystem>
#include <unordered_map>

#include "dist.h"

std::unordered_map<std::string, std::filesystem::path> InitializeEnvironment();

#endif // ENV_H