"""
This script generates reStructuredText (RST) documentation files for the "bookmarks"
Python project. It:

- Recursively scans the 'bookmarks' directory to identify packages, non-package directories,
  and modules.
- Treats all directories containing Python files (or subdirectories that do) as part of
  the documentation structure.
- Packages (directories with __init__.py) get their docstring extracted and included,
  along with an `.. automodule::` directive.
- Non-package directories are documented as namespaces; they don't get an `.. automodule::`,
  but still produce an `index.rst` listing their subdirectories and modules.
- Each module (individual .py file) gets its own .rst file with `.. automodule::`.
- Clears and recreates the modules directory on each run.

This ensures a fully recursive and comprehensive set of RST files that reflect
the entire codebase structure.
"""

import ast
import logging
import os
import shutil

# ----------------------- Path Configuration -----------------------

# Construct paths using os.path.join and os.path.abspath for reliability
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_MODULE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'bookmarks'))
PYTHON_MODULE_DOCS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, 'rst'))

# ----------------------- Directory Preparation -----------------------

# Clear and recreate the modules directory each run
if os.path.isdir(PYTHON_MODULE_DOCS_DIR):
    try:
        shutil.rmtree(PYTHON_MODULE_DOCS_DIR)
        print(f"Removed existing documentation directory: {PYTHON_MODULE_DOCS_DIR}")
    except Exception as e:
        print(f"Failed to remove existing documentation directory: {e}")
        raise
os.makedirs(PYTHON_MODULE_DOCS_DIR, exist_ok=True)
print(f"Created documentation directory: {PYTHON_MODULE_DOCS_DIR}")

if not os.path.isdir(PYTHON_MODULE_DIR):
    raise RuntimeError(f'Could not find the source directory: {PYTHON_MODULE_DIR}')

# ----------------------- Logging Configuration -----------------------

# Configure logging to write to the new RST directory
LOG_FILE = os.path.join(PYTHON_MODULE_DOCS_DIR, 'rst_generator.log')

# Set up the root logger
logging.basicConfig(
    level=logging.DEBUG,  # Capture all levels of log messages
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),  # Log to file
        logging.StreamHandler()  # Log to console
    ]
)

logging.info("Starting RST documentation generator script.")
logging.debug(f'PYTHON_MODULE_DIR: {PYTHON_MODULE_DIR}')
logging.debug(f'PYTHON_MODULE_DOCS_DIR: {PYTHON_MODULE_DOCS_DIR}')


# ----------------------- Function Definitions -----------------------

def extract_docstring(pyfile):
    """
    Extracts the docstring from a Python file.
    """
    try:
        with open(pyfile, 'r', encoding='utf-8') as f:
            source = f.read()
        module = ast.parse(source)
        docstring = ast.get_docstring(module) or ""
        logging.debug(f"Extracted docstring from {pyfile}")
        return docstring
    except Exception as e:
        logging.warning(f"Failed to extract docstring from {pyfile}: {e}")
        return ""


def is_package(dir_path):
    """
    Determines if a directory is a Python package by checking for __init__.py.
    """
    package = os.path.isfile(os.path.join(dir_path, '__init__.py'))
    logging.debug(f"Directory '{dir_path}' is_package: {package}")
    return package


def find_python_items(dir_path):
    """
    Identify subdirectories and modules (.py files) in dir_path.
    Returns (subdirs, modules):
      subdirs: list of directories that contain python files (package or not)
      modules: list of python modules (no __init__.py)
    """
    subdirs = []
    modules = []
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                if entry.is_dir() and entry.name != '__pycache__':
                    # Check recursively if this subdir contains python files
                    if contains_python_files(entry.path):
                        subdirs.append(entry.path)
                        logging.debug(f"Found subdirectory with Python files: {entry.path}")
                elif entry.is_file() and entry.name.endswith('.py') and entry.name != '__init__.py':
                    modules.append(entry.path)
                    logging.debug(f"Found module: {entry.path}")
    except Exception as e:
        logging.error(f"Error scanning directory '{dir_path}': {e}")
    return subdirs, modules


def contains_python_files(dir_path):
    """
    Check if directory (recursively) contains any .py files.
    """
    try:
        for root, dirs, files in os.walk(dir_path):
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            for file in files:
                if file.endswith('.py'):
                    logging.debug(f"Directory '{dir_path}' contains Python file: {file}")
                    return True
    except Exception as e:
        logging.error(f"Error walking through directory '{dir_path}': {e}")
    return False


def get_short_name(full_name):
    """
    Extracts the short name from a fully qualified module name.
    Example:
        'bookmarks.common' -> 'common'
        'bookmarks.templates.error' -> 'error'
    """
    return full_name.split('.')[-1]


def build_structure(dir_path):
    """
    Build a structure dict for the directory `dir_path`.

    The structure is a dict:
    {
      'name': str (the dotted module name or relative name),
      'path': str (the actual file system path),
      'is_package': bool,
      'docstring': str (package docstring if package),
      'subsections': [ ... ] (list of subsection dicts),
      'modules': [ ... ] (list of dotted module names)
    }

    If dir_path is within bookmarks, 'name' is the dotted name like 'bookmarks',
    'bookmarks.common', etc. For non-package dirs, we still give them a dotted name by
    replacing slashes with dots, just without an automodule directive.
    """
    try:
        rel_path = os.path.relpath(dir_path, PYTHON_MODULE_DIR)
        if rel_path == '.':
            name = 'bookmarks'
        else:
            # Replace OS-specific separators with dots
            name = 'bookmarks.' + rel_path.replace(os.sep, '.')
        logging.debug(f"Building structure for '{name}'")
        package = is_package(dir_path)

        docstring = ""
        if package:
            init_file = os.path.join(dir_path, '__init__.py')
            # Manual extraction is removed to prevent duplication
            # docstring = extract_docstring(init_file)

        subdirs, modules_paths = find_python_items(dir_path)
        modules = []
        for m_path in sorted(modules_paths):
            # Convert module file path to dotted name
            rel_mod_path = os.path.relpath(m_path, PYTHON_MODULE_DIR)
            # Updated module name construction with 'bookmarks.' prefix
            mod_name = 'bookmarks.' + rel_mod_path.replace(os.sep, '.').replace('.py', '')
            modules.append(mod_name)
            logging.debug(f"Module '{mod_name}' added to '{name}'")

        subsections = []
        for sdir in sorted(subdirs):
            subsections.append(build_structure(sdir))

        return {
            'name': name,
            'path': dir_path,
            'is_package': package,
            # 'docstring': docstring,  # Removed to prevent duplication
            'subsections': subsections,
            'modules': modules
        }
    except Exception as e:
        logging.error(f"Error building structure for '{dir_path}': {e}")
        return {
            'name': 'unknown',
            'path': dir_path,
            'is_package': False,
            'docstring': "",
            'subsections': [],
            'modules': []
        }


def write_index_rst(section):
    """
    Write an index.rst for a given section (package or non-package directory).
    """
    try:
        pkg_path = section['name'].replace('.', os.sep)
        rst_dir = os.path.join(PYTHON_MODULE_DOCS_DIR, pkg_path)
        os.makedirs(rst_dir, exist_ok=True)
        logging.debug(f"Writing index.rst in '{rst_dir}'")

        rst_file = os.path.join(rst_dir, 'index.rst')

        # Extract short name for the title
        short_title = get_short_name(section['name'])
        title = short_title
        title_underline = '=' * len(title)

        # Build toctree entries relative to the current section
        toctree_entries = []
        current_name = section['name']
        for ssec in section['subsections']:
            # Relative name by removing the current section's name and the dot
            relative_name = ssec['name'][len(current_name) + 1:]
            entry = os.path.join(relative_name.replace('.', os.sep), 'index')
            entry = entry.replace('\\', '/').strip('/\\')  # Ensure forward slashes and no leading/trailing
            toctree_entries.append(entry)
            logging.debug(f"Toctree entry added (subsection): {entry}")
        for mod in section['modules']:
            relative_mod = mod[len(current_name) + 1:]
            entry = relative_mod.replace('.', '/').strip('/\\')
            toctree_entries.append(entry)
            logging.debug(f"Toctree entry added (module): {entry}")

        with open(rst_file, 'w', encoding='utf-8') as f:
            f.write('.. meta::\n')
            f.write('    :description: Developer documentation page for the Bookmarks python modules\n')
            f.write('    :keywords: Bookmarks, bookmarksvfx, pipeline, asset manager, PySide, Qt, Python, vfx\n\n')

            f.write(title + '\n')
            f.write(title_underline + '\n\n')

            # If it's a package, include automodule
            if section['is_package']:
                f.write(f'.. automodule:: {section["name"]}\n')
                f.write('    :members:\n')
                f.write('    :show-inheritance:\n\n')

            if toctree_entries:
                f.write('.. toctree::\n')
                f.write('    :maxdepth: 2\n\n')
                for entry in toctree_entries:
                    f.write(f'    {entry}\n')
                f.write('\n')

        logging.info(f"Written index.rst: {rst_file}")
    except Exception as e:
        logging.error(f"Failed to write index.rst for section '{section['name']}': {e}")


def write_module_rst(mod_name):
    """
    Write an rst file for an individual module.
    """
    try:
        mod_path = mod_name.replace('.', os.sep)
        rst_dir = os.path.dirname(os.path.join(PYTHON_MODULE_DOCS_DIR, mod_path))
        os.makedirs(rst_dir, exist_ok=True)
        logging.debug(f"Writing module RST in '{rst_dir}'")

        rst_file = os.path.join(PYTHON_MODULE_DOCS_DIR, mod_path + '.rst')

        # Extract short name for the title
        short_title = get_short_name(mod_name)
        title = short_title
        title_underline = '=' * len(title)

        with open(rst_file, 'w', encoding='utf-8') as f:
            f.write('.. meta::\n')
            f.write('    :description: Developer documentation page for the Bookmarks python modules\n')
            f.write('    :keywords: Bookmarks, bookmarksvfx, pipeline, asset manager, PySide, Qt, Python, vfx\n\n')
            f.write(title + '\n')
            f.write(title_underline + '\n\n')
            f.write(f'.. automodule:: {mod_name}\n')
            f.write('    :members:\n')
            f.write('    :show-inheritance:\n\n')

        logging.info(f"Written module RST: {rst_file}")
    except Exception as e:
        logging.error(f"Failed to write module RST for '{mod_name}': {e}")


def write_structure(section):
    """
    Recursively write out the structure:
    - index.rst for each directory
    - .rst files for each module
    - Then recurse into subsections
    """
    # Write index for current section (directory)
    write_index_rst(section)

    # Write modules
    for mod in section['modules']:
        write_module_rst(mod)

    # Recurse into subsections
    for ssec in section['subsections']:
        write_structure(ssec)


# ----------------------- Main Execution -----------------------


def main():
    try:
        logging.info('Generating documentation structure...')
        structure = build_structure(PYTHON_MODULE_DIR)

        # Create top-level index that references bookmarks/index
        top_index = os.path.join(PYTHON_MODULE_DOCS_DIR, 'index.rst')
        try:
            with open(top_index, 'w', encoding='utf-8') as f:
                f.write('Bookmarks Documentation\n')
                f.write('======================\n\n')
                f.write('.. toctree::\n')
                f.write('    :maxdepth: 2\n\n')
                f.write('    bookmarks/index\n\n')
            logging.info(f"Written top-level index.rst: {top_index}")
        except Exception as e:
            logging.error(f"Failed to write top-level index.rst: {e}")

        write_structure(structure)
        logging.info('Documentation generation complete.')
    except Exception as e:
        logging.critical(f"Script terminated unexpectedly: {e}")
        raise


if __name__ == '__main__':
    main()
