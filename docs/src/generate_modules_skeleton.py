"""This script generates the rst files for the modules in the bookmarks package.

Use it in conjunction with make.bat to generate the documentation.

"""
import os

PYTHON_MODULE_DIR = os.path.normpath(f'{__file__}/{os.pardir}/{os.pardir}/{os.pardir}/bookmarks').replace('\\', '/')
print(f'>>> PYTHON_MODULE_DIR: {PYTHON_MODULE_DIR}')

PYTHON_MODULE_DOCS_DIR = os.path.normpath(f'{__file__}/{os.pardir}/modules').replace('\\', '/')
print(f'>>> PYTHON_MODULE_DOCS_DIR: {PYTHON_MODULE_DOCS_DIR}')

if not os.path.isdir(PYTHON_MODULE_DOCS_DIR):
    raise RuntimeError(f'Could not find the docs directory: {PYTHON_MODULE_DOCS_DIR}')

if not os.path.isdir(PYTHON_MODULE_DIR):
    raise RuntimeError(f'Could not find the source directory: {PYTHON_MODULE_DIR}')


def recursive_search(_path):
    if '__pycache__' in _path:
        return

    print(f'>>> Searching for modules in: {_path}')
    with os.scandir(_path) as it:
        for _entry in it:
            if _entry.is_dir():
                yield from recursive_search(_entry.path.replace('\\', '/'))
            else:
                yield _entry



if __name__ == '__main__':
    print('>>> Generating the documentation for the bookmarks package:')
    print(f'>>> Source: {PYTHON_MODULE_DIR}')

    _source = '/'.join(PYTHON_MODULE_DIR.split('/')[:-1])
    contents = []

    # Generate the index bookmarks.rst file
    with open(f'{PYTHON_MODULE_DOCS_DIR}/bookmarks.rst', 'w') as f:
        f.write(f'.. meta::\n')
        f.write(f'    :description: Developer documentation page for the Bookmarks python modules\n')
        f.write(
            f'    :keywords: Bookmarks, bookmarksvfx, pipeline, pipe, asset manager, assets, PySide, Qt, PySide,'
            f'Python, vfx, animation, film, production, open-source, opensource, ShotGun, ShotGrid, RV, '
            f'ffmpeg, openimageio, publish, manage, digital content management\n'
            )
        f.write(f'\n')
        f.write(f'bookmarks\n')
        f.write(f'=========\n')
        f.write(f'\n')
        f.write(f'.. automodule:: bookmarks\n')
        f.write(f'    :members:\n')
        f.write(f'    :show-inheritance:\n')
        f.write(f'\n')
        f.write(f'.. toctree::\n')
        f.write(f'    :glob:\n')
        f.write(f'\n')
        f.write(f'    bookmarks/**\n')
        f.write(f'\n')

    for entry in recursive_search(PYTHON_MODULE_DIR):
        if not entry.name.endswith('.py'):
            continue

        path = entry.path.replace('\\', '/')

        parent = os.path.join(path, os.pardir)
        basemod = os.path.normpath(parent).replace('\\', '/').replace(_source, '').strip('/')
        basemod = basemod if basemod else 'bookmarks'

        if entry.name == '__init__.py':
            rst_dir = f'{PYTHON_MODULE_DOCS_DIR}/{basemod}'
            rst_file = f'{rst_dir}/{basemod}.rst'
            print(f'>>> Module found: {rst_dir}')
            os.makedirs(rst_dir, exist_ok=True)
            continue

        basename = path.replace(_source, '').strip('/').replace('.py', '.rst')
        basename = basename if basename else 'bookmarks'
        rst_file = f'{PYTHON_MODULE_DOCS_DIR}/{basename}'

        os.makedirs(os.path.dirname(rst_file), exist_ok=True)

        with open(rst_file, 'w') as f:
            print(f'>>> Generating rst for: {path}')

            f.write(f'.. meta::\n')
            f.write(f'    :description: Developer documentation page for the Bookmarks python modules\n')
            f.write(
                f'    :keywords: Bookmarks, bookmarksvfx, pipeline, pipe, asset manager, assets, PySide, Qt, PySide,'
                f'Python, vfx, animation, film, production, open-source, opensource, ShotGun, ShotGrid, RV, '
                f'ffmpeg, openimageio, publish, manage, digital content management\n'
                )
            f.write(f'\n')
            title = '.'.join(basename.replace(".rst", '').split('/')[1:])
            f.write(f'{title}\n')
            f.write('=' * (len(basemod) + 10) + '\n')
            f.write(f'\n')
            f.write(f'.. automodule:: {basename.replace("/", ".").replace(".rst", "")}\n')
            f.write('    :members:\n')
            f.write('    :show-inheritance:\n')


