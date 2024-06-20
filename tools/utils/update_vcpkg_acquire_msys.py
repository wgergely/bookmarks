"""
VCPKG utility script to update msys2 package URLs and SHA512 checksums in a
given repository.

It checks for updates in the specified MSYS2 and MinGW repositories, compares them with the current packages defined in the cmake files,
and updates the files with new versions and checksums if necessary.

Usage:
    Run this script via the command line with the path to the vcpkg repository folder.
    Example: python update_vcpkg_acquire_msys.py --path /path/to/vcpkg

"""
import argparse
import hashlib
import os
import re
from urllib.parse import unquote, quote

import requests


def get_sha512_of_package(url):
    sha512 = hashlib.sha512()
    r = requests.get(url, stream=True)
    for chunk in r.iter_content(chunk_size=8192):
        sha512.update(chunk)
    return sha512.hexdigest()


def extract_package_name(url, repo):
    return (
        url.
        replace(f'{repo}/', '').
        replace('-x86_64.pkg.tar.zst', '').
        replace('-x86_64.pkg.tar.xz', '').
        replace('-x86_64.pkg.tar.gz', '').
        replace('-any.pkg.tar.zst', '').
        replace('-any.pkg.tar.xz', '').
        replace('-any.pkg.tar.gz', '').
        replace(f'mingw-w64-x86_64-', '').
        replace(f'mingw-w64-i686-', '')
    ).strip('/')


def _main(path):
    m_url = re.compile(r'.*\"(https?://.*)\".*', re.IGNORECASE)
    m_sha = re.compile(r'.*?([0-9a-f]{128}).*?', re.IGNORECASE)
    m_a = re.compile(r'.*a href=\"(.*)\"', re.IGNORECASE)
    m_pkg = re.compile(r'^([\w.\-+]*)-(git-.*?|[\da-z~+_.]*)-(\d+)$', re.IGNORECASE)

    repos = (
        'https://repo.msys2.org/msys/x86_64',
        'https://repo.msys2.org/mingw/x86_64',
        'https://repo.msys2.org/mingw/i686'
    )

    with open(path, 'r') as f:
        lines = f.readlines()

    for repo in repos:
        print(f'[info] Checking {repo}')

        current_packages, packages_to_update = {}, {}

        for i, line in enumerate(lines):
            if not line.strip():
                continue
            match = m_url.match(line)
            if not match:
                continue
            url = match.group(1)

            # Skip if this is not the repository we are looking for
            if repo not in url:
                continue

            package_name = extract_package_name(url, repo)

            # Extract package name, version, and build number
            _match = m_pkg.match(package_name)
            if not _match:
                print(f'[error] {package_name} does not match the package name pattern. Skipping.')
                continue

            try:
                package_name, version, build = _match.group(1), _match.group(2), _match.group(3)
            except:
                print(f'[error] Failed to match package name, version, and build number for {package_name}. Skipping.')
                continue

            if package_name not in current_packages:
                print(f'[info] Found defined package {package_name} @ {repo}')

                current_packages[package_name] = {
                    'url': url,
                    'sha': m_sha.match(lines[i + 1]).group(1),
                    'versions': []
                }

            current_packages[package_name]['versions'].append(f'{version}-{build}')

        # Check the repository for updates
        print(f'[info] Checking {repo} for updates...')

        response = requests.get(repo).text
        for line in response.split('\n'):
            line = unquote(line)

            # Extract package name from <a></a> tag
            match = m_a.match(line)
            if not match:
                continue
            filename = match.group(1)

            # Skip signature and old packages
            if filename.endswith('.sig'):
                continue
            if filename.endswith('.old'):
                continue

            package_name = extract_package_name(filename, repo)

            _match = m_pkg.match(package_name)
            if not _match:
                print(f'[error] {package_name} does not match the package name pattern. Skipping.')
                continue

            try:
                package_name, version, build = _match.group(1), _match.group(2), _match.group(3)
            except:
                print(f'[error] Failed to match package name, version, and build number for {package_name}. Skipping.')
                continue

            if package_name not in current_packages:
                continue

            version = f'{version}-{build}'
            if version in current_packages[package_name]['versions']:
                continue

            if package_name not in packages_to_update:
                print(f'[info] Found new version for {package_name} at {repo}/{quote(match.group(1))}')

                packages_to_update[package_name] = {
                    'url': f'{repo}/{quote(filename)}',
                    'versions': []
                }

            packages_to_update[_match.group(1)]['versions'].append(version)

        # Find the latest version
        for package in packages_to_update:
            latest = packages_to_update[package]['versions'][-1]
            packages_to_update[package]['latest'] = latest

            print(f'[info] Calculating SHA512 checksum for {package} {latest}...')
            packages_to_update[package]['sha'] = get_sha512_of_package(packages_to_update[package]['url'])

        print(f'[info] Updating {path}...')

        with open(path, 'r') as f:
            text = f.read()

        for k in packages_to_update:
            if k not in current_packages:
                continue

            if current_packages[k]['url'] in text:
                print(f'[info] {current_packages[k]["url"]} -> {packages_to_update[k]["url"]}')
                text = text.replace(current_packages[k]['url'], packages_to_update[k]['url'])
            else:
                print(f'[error] {current_packages[k]["url"]} not found in {vcpkg_acquire_msys_file}. Skipping.')

            if current_packages[k]['sha'] in text:
                print(f'[info] {current_packages[k]["sha"]} -> {packages_to_update[k]["sha"]}')
                text = text.replace(current_packages[k]['sha'], packages_to_update[k]['sha'])
            else:
                print(f'[error] {current_packages[k]["sha"]} not found in {vcpkg_acquire_msys_file}. Skipping.')

        print(f'[info] Writing changes to {path}...')
        with open(path, 'w') as f:
            f.write(text)

        print(f'[info] Done.')


def main(vcpkg):
    if not vcpkg or not isinstance(vcpkg, str):
        raise ValueError('No path provided.')
    if not os.path.isdir(vcpkg):
        raise ValueError('Invalid path provided. Provide a valid path to the vcpkg folder.')

    vcpkg_acquire_msys_file = f'{vcpkg}/scripts/cmake/vcpkg_acquire_msys.cmake'
    if not os.path.isfile(vcpkg_acquire_msys_file):
        raise FileNotFoundError('vcpkg_acquire_msys.cmake file not found.')

    vcpkg_find_fortran_file = f'{vcpkg}/scripts/cmake/vcpkg_find_fortran.cmake'
    if not os.path.isfile(vcpkg_find_fortran_file):
        raise FileNotFoundError('vcpkg_find_fortran.cmake file not found.')

    vcpkg_find_acquire_program_file = f'{vcpkg}/scripts/cmake/vcpkg_find_acquire_program.cmake'
    if not os.path.isfile(vcpkg_find_acquire_program_file):
        raise FileNotFoundError('vcpkg_find_acquire_program.cmake file not found.')

    _main(vcpkg_acquire_msys_file)
    _main(vcpkg_find_fortran_file)
    _main(vcpkg_find_acquire_program_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update MSYS2 package URLs and SHA512 checksums.")
    parser.add_argument("--path", required=True, help="Path to the vcpkg repository.")
    args = parser.parse_args()
    main(args.path)
