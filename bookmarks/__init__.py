""".. centered:: |logo| |image1|

.. centered:: |label1| |label2| |label3| |label4|


Bookmarks is a lightweight Python asset manager designed to browse and manage the content of animation, VFX and film
projects.

------------

.. centered:: :ref:`User Guide`  |  :ref:`Python Modules`  |  :ref:`Get Bookmarks`

------------


Features
------------


The app categorises  project content as separate :mod:`bookmarks<bookmarks.items.bookmark_items>`,
:mod:`assets<bookmarks.items.asset_items>` and :mod:`file items<bookmarks.items.file_items>`.
You can configure these independently to link with, for instance, ShotGrid entities or
configure their properties like frame rate and resolution to set :mod:`Maya scene settings <bookmarks.maya.plugin>`.
You can use filters to sort and hide items, preview images, convert footage sequences, or 'publish' files.
See :ref:`User Guide` for more information.

Background
------------

I developed the app to help manage personal projects and keep myself organised (I'm a digitally messy person). So,
whilst it works great for me, it might not work for you. Still, I tried to make it easily customisable to help adapt
to site-specific environments. See the python modules documentation for more information.

Quick Start
-------------

The simplest way to start Bookmarks as a standalone application is to run:

.. code-block:: python
    :linenos:

    import bookmarks
    bookmarks.exec_()


Dependencies
--------------------

The release contains all Windows dependencies. For setting up a custom development environment on another platform,
you'll need the following python dependencies:

* `Python3 <https://github.com/python/cpython>`_ -  Tested against 3.9
* `PySide2 <https://pypi.org/project/PySide2>`_ - Tested against Qt 5.15.2
* `OpenImageIO <https://github.com/OpenImageIO/oiio>`_ - Tested against 2.3
* `numpy <https://pypi.org/project/numpy>`_
* `psutil <https://pypi.org/project/psutil>`_
* `shotgun_api3 <https://github.com/shotgunsoftware/python-api>`_

.. note:

    * Currently, Windows is the only supported platform (although much of the codebase should be platform-agnostic).
    * OpenImageIO does not currently maintain installable python packages.


.. |logo| image:: _static/icon.png
   :height: 200
   :width: 200
   :alt: Bookmarks - Lightweight asset manager designed for VFX, animation, film productions

.. |label1| image:: https://img.shields.io/badge/Python-3.8%2B-lightgrey
   :height: 18

.. |label2| image:: https://img.shields.io/badge/Python-PySide2-lightgrey
   :height: 18

.. |label3| image:: https://img.shields.io/badge/Platform-Windows-lightgrey
   :height: 18

.. |label4| image:: https://img.shields.io/badge/Version-v0.9.2-green
   :height: 18

.. |image1| image:: ./images/active_bookmark.png
    :width: 480


"""
import importlib
import platform
import sys

from PySide2 import QtWidgets

#: Package author
__author__ = 'Gergely Wootsch'

#: Project homepage
__website__ = 'https://bookmarks-vfx.com'

#: Author email
__email__ = 'hello@gergely-wootsch.com'

#: Project version
__version__ = '0.9.2'

#: Project version
__version_info__ = __version__.split('.')

#: Project copyright
__copyright__ = f'Copyright (c) 2024 {__author__}'

# Specify python support
if sys.version_info[0] < 3 and sys.version_info[1] < 9:
    raise RuntimeError('Bookmarks requires Python 3.9.0 or later.')


def info():
    """Returns an informative string about the project environment and author.

    Returns:
        str: An informative string.

    """
    py_ver = platform.python_version()
    py_c = platform.python_compiler()
    oiio_ver = importlib.import_module('OpenImageIO').__version__
    qt_ver = importlib.import_module('PySide2.QtCore').__version__
    sg_ver = importlib.import_module('shotgun_api3').__version__

    return '\n'.join(
        (
            __copyright__,
            f'E-Mail: {__email__}',
            f'Website: {__website__}',
            '\nPackages\n'
            f'Python {py_ver} {py_c}',
            f'Bookmarks {__version__}',
            f'PySide2 {qt_ver}',
            f'OpenImageIO {oiio_ver}',
            f'ShotGrid API {sg_ver}',
        )
    )


def exec_(print_info=True):
    """Initializes all required submodules and data and launches shows the app's main window.

    """
    from . import common
    with common.initialize(common.Mode.Standalone, run_app=True) as app:
        if print_info:
            print(info())

        from . import standalone
        standalone.show()
