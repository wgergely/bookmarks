import os

SOURCE = os.path.normpath(f'{__file__}/{os.pardir}/{os.pardir}/{os.pardir}/bookmarks').replace('\\', '/')
DOCS_DIR = os.path.normpath(f'{__file__}/{os.pardir}/modules').replace('\\', '/')

def recursive_search(path):
    for entry in os.scandir(path):
        if entry.is_dir():
            yield from recursive_search(entry.path)
        else:
            yield entry


_source = '/'.join(SOURCE.split('/')[:-1])
contents = []

for entry in recursive_search(SOURCE):
    if not entry.name.endswith('.py'):
       continue

    path = entry.path.replace('\\', '/')

    parent = os.path.join(path, os.pardir)
    basemod = os.path.normpath(parent).replace('\\', '/').replace(_source, '').strip('/')
    basemod = basemod if basemod else 'bookmarks'

    if entry.name == '__init__.py':
        rst_dir = f'{DOCS_DIR}/{basemod}'
        rst_file = f'{rst_dir}/{basemod}.rst'

        if not os.path.isdir(rst_dir):
            os.makedirs(rst_dir)
        continue

    basename = path.replace(_source, '').strip('/').replace('.py', '.rst')
    basename = basename if basename else 'bookmarks'
    rst_file = f'{DOCS_DIR}/{basename}'
    with open(rst_file, 'w') as f:
        f.write(f'.. meta::\n')
        f.write(f'    :description: Developer documentation page for the Bookmarks python modules\n')
        f.write(f'    :keywords: Bookmarks, bookmarksvfx, asset manager, assets, PySide, Qt5, PySide2, Python, vfx, animation, film, productivity, free, open-source, opensource, lightweight, ShotGrid, RV, FFMpeg, ffmpeg, publish, manage, digital content management, production, OpenImageIO\n')
        f.write(f'\n')
        title = '.'.join(basename.replace(".rst", '').split('/')[1:])
        f.write(f'{title}\n')
        f.write('=' * (len(basemod) + 10) + '\n')
        f.write(f'\n')
        f.write(f'.. automodule:: {basename.replace("/", ".").replace(".rst", "")}\n')
        f.write('    :members:\n')
        f.write('    :show-inheritance:\n')