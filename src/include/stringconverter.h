#ifndef STRINGCONVERTER_H
#define STRINGCONVERTER_H

#include <locale>
#include <string>

#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h> // For MultiByteToWideChar and WideCharToMultiByte
#else
#include <codecvt> // For std::codecvt_utf8 (deprecated in C++17)
#endif

class StringConverter
{
public:
    static std::wstring to_wstring(const std::string &utf8Str)
    {
#ifdef _WIN32
        int count = MultiByteToWideChar(CP_UTF8, 0, utf8Str.c_str(), -1, nullptr, 0);
        std::wstring wideStr(count, 0);
        MultiByteToWideChar(CP_UTF8, 0, utf8Str.c_str(), -1, &wideStr[0], count);
        return wideStr;
#else
        std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;
        return converter.from_bytes(utf8Str);
#endif
    }

    static std::string to_string(const std::wstring &wideStr)
    {
#ifdef _WIN32
        int count = WideCharToMultiByte(CP_UTF8, 0, wideStr.c_str(), -1, nullptr, 0, nullptr, nullptr);
        std::string utf8Str(count, 0);
        WideCharToMultiByte(CP_UTF8, 0, wideStr.c_str(), -1, &utf8Str[0], count, nullptr, nullptr);
        return utf8Str;
#else
        std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;
        return converter.to_bytes(wideStr);
#endif
    }
};

#endif // STRINGCONVERTER_H