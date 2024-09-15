
#ifndef COMMAND_LINE_PARSER_H
#define COMMAND_LINE_PARSER_H

#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

class CommandLineParser
{
public:
    struct ArgumentSpec
    {
        std::vector<std::wstring> names; // Include both short and long names here
        std::wstring description;
        std::optional<std::wstring> defaultValue;
        bool requiresValue = false;
        bool required = false;
    };

private:
    std::map<std::wstring, ArgumentSpec> specs;
    std::map<std::wstring, std::wstring> parsedArgs;
    std::map<std::wstring, std::wstring> aliasMap; // Map aliases to primary names

    void buildAliasMap()
    {
        for (const auto &spec : specs)
        {
            for (const auto &name : spec.second.names)
            {
                aliasMap[name] = spec.first;
            }
        }
    }

    void initializeDefaults()
    {
        for (const auto &spec : specs)
        {
            if (spec.second.defaultValue.has_value())
            {
                parsedArgs[spec.first] = spec.second.defaultValue.value();
            }
            else if (!spec.second.requiresValue)
            {
                // If it doesn't require a value and no default is specified, initialize
                // with an empty string
                parsedArgs[spec.first] = L"";
            }
        }
    }

public:
    CommandLineParser(std::initializer_list<std::pair<const std::wstring, ArgumentSpec>> list)
    {
        for (const auto &item : list)
        {
            specs[item.first] = item.second;
        }
        buildAliasMap();
        initializeDefaults();
    }

    void parse(int argc, wchar_t *argv[])
    {
        for (int i = 1; i < argc; ++i)
        {
            std::wstring arg = argv[i];
            std::wstring primaryName;

            // Find the primary argument name for the given alias
            auto aliasIt = aliasMap.find(arg);
            if (aliasIt != aliasMap.end())
            {
                primaryName = aliasIt->second;
            }
            else
            {
                throw std::runtime_error("Unknown argument: " + std::string(arg.begin(), arg.end()));
            }

            const auto &spec = specs[primaryName];
            if (spec.requiresValue)
            {
                if ((i + 1) < argc && argv[i + 1][0] != L'-')
                {
                    parsedArgs[primaryName] = argv[++i];
                }
                else
                {
                    throw std::runtime_error("Argument requires a value but none was provided.");
                }
            }
            else
            {
                parsedArgs[primaryName] = spec.defaultValue.value_or(L"");
            }
        }

        for (const auto &spec : specs)
        {
            if (spec.second.required && parsedArgs.find(spec.first) == parsedArgs.end())
            {
                throw std::runtime_error("Missing required argument: " +
                                         std::string(spec.first.begin(), spec.first.end()));
            }
        }
    }

    template <typename T>
    T get(const std::wstring &name) const
    {
        auto it = parsedArgs.find(name);
        if (it != parsedArgs.end())
        {
            T value;
            std::wistringstream wiss(it->second);
            if (!(wiss >> value))
            {
                throw std::runtime_error("Invalid argument value for: " + std::string(name.begin(), name.end()));
            }
            return value;
        }

        throw std::runtime_error("Argument not found: " + std::string(name.begin(), name.end()));
    }

    bool has(const std::wstring &name) const { return parsedArgs.find(name) != parsedArgs.end(); }

    void showHelp() const
    {
        std::wcout << L"Usage instructions:\n";
        for (const auto &specItem : specs)
        {
            const auto &spec = specItem.second;
            std::wstring names = join(spec.names, L", ");
            std::wstring defaultValue = spec.defaultValue.has_value() ? spec.defaultValue.value() : L"";
            std::wcout << L"  " << names << L"\t" << spec.description;
            if (!defaultValue.empty())
            {
                std::wcout << L" (default: " << defaultValue << L")";
            }
            std::wcout << std::endl;
        }
    }

    static std::wstring join(const std::vector<std::wstring> &vec, const std::wstring &delimiter)
    {
        std::wstring result;
        for (auto it = vec.begin(); it != vec.end(); ++it)
        {
            if (it != vec.begin())
            {
                result += delimiter;
            }
            result += *it;
        }
        return result;
    }
};

#endif // COMMAND_LINE_PARSER_H