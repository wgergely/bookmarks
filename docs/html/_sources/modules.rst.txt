.. meta::
    :description: Bookmarks: A free and open-source asset manager for film, animation and VFX projects.
    :keywords: Bookmarks, asset manager, assets, PySide, Qt5, PySide2, Python, vfx, animation, film, productivity, free, open-source, opensource, lightweight, ShotGrid, RV, FFMpeg, ffmpeg, publish, manage, digital content management, production, OpenImageIO


=====================
Python Modules
=====================


Bookmarks works by parsing project folders to find bookmark, asset and file items.
Check out the :mod:`~bookmarks.items.bookmark_items`, :mod:`~bookmarks.items.asset_items`
and :mod:`~bookmarks.items.file_items` for an overview of the item definitions.

The application resources are stored in the ``rsc`` folder. Basic properties can be
customized by modifying the ``rsc/config.json`` file.

The application stylesheet is defined by ``rsc/stylesheet.json``.

The :mod:`bookmarks.common` module contains components that define core functionality.

The list item models and views are defined in the :mod:`bookmarks.items` module.


Index
=====


.. toctree::
    :maxdepth: 4
    :glob:

    modules/*



