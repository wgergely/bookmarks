.. meta::
    :description: Developer documentation page for the Bookmarks python modules
    :keywords: Bookmarks, asset manager, assets, PySide, Qt5, PySide2, Python, vfx, animation, film, productivity, free, open-source, opensource, lightweight, ShotGrid, RV, FFMpeg, ffmpeg, publish, manage, digital content management, production, OpenImageIO


=====================
Python Modules
=====================


Bookmarks works by parsing project folders to find bookmark, asset and file items.
Check out the :mod:`~bookmarks.items.bookmark_items`, :mod:`~bookmarks.items.asset_items`
and :mod:`~bookmarks.items.file_items` for an overview of the item definitions.

The application resources are stored in the ``rsc`` folder. Basic properties can be
customized by modifying the ``rsc/config.json`` file. The application stylesheet is
defined by ``rsc/stylesheet.qss``.


Development environment
-------------------------------

The default line length is 90 characters. Docstring follow the Google Style Python
Docstring - https://google.github.io/styleguide/pyguide.html, and code formatting follows
the PyCharm defaults.


Index
-------------------------------


.. grid:: 1 1 2 2
    :gutter: 1 1 5 5

    .. grid-item-card::

        **Bookmark, asset and file items**
        ^^^

        See :mod:`~bookmarks.items.bookmark_items`, :mod:`~bookmarks.items.asset_items`,
        and :mod:`~bookmarks.items.file_items` for an overview on how items are
        loaded and cached.

    .. grid-item-card::

        **Core functions and classes**
        ^^^
        :mod:`~bookmarks.common`

        The top module used across the application. It contains most basic components needed
        run the app. It defines size, color information and data types and caches.

        Are you trying to get Bookmarks up and running? Check out
        :func:`~bookmarks.common.setup.initialize` and
        :func:`~bookmarks.common.setup.uninitialize` functions.


    .. grid-item-card::

        **Property storage**
        ^^^

        :mod:`~bookmarks.database`

        User configured item data is stored in SQLite databases.

        :mod:`~bookmarks.common.settings`

        Current context and ui state information is stored in a customized QSettings
        instance.


    .. grid-item-card::

        **Image resources**
        ^^^

        :mod:`~bookmarks.images`

        Most image manipulation methods are stored in this module.
        Bookmarks uses OpenImageIO to create image thumbnails, e.g.
        :meth:`~bookmarks.images.ImageCache.oiio_make_thumbnail`.

        See :class:`~bookmarks.images.ImageCache` for the getting and caching image
        resources.


    .. grid-item-card::

        **Main ui components**
        ^^^

        The main widget is made up of a :mod:`~bookmarks.main` widget, :mod:`~bookmarks.topbar`,
        and a :mod:`~bookmarks.statusbar`.

        The main widget also contains the main :mod:`item <bookmarks.items>` tabs.
        See :mod:`~bookmarks.items.views` for details.

        Context menu definitions and actions can be found in the
        :mod:`~bookmarks.contextmenu` and :mod:`~bookmarks.actions` modules.
        Global shortcuts are defined in the :mod:`~bookmarks.shortcuts` module.

        The item views are backed by helper threads defined in :mod:`~bookmarks.threads`.


    .. grid-item-card::

        **Item properties and editors**
        ^^^

        Bookmark and asset items have their own bespoke properties we edit using
        a generalised editor widget defined in :mod:`bookmarks.editor.base`.

        The same widget is used to edit
        :mod:`application preferences <bookmarks.editor.preferences>`.

        Some of the item properties have their own modules. See :mod:`bookmarks.tokens`
        and the :mod:`bookmarks.launcher` modules.

        Property import and export functions are found in :mod:`~bookmarks.importexport`.


    .. grid-item-card::

        **Maya module**
        ^^^
        Maya related functionality can be found in the :mod:`bookmarks.modules.maya`
        The installable maya plugins is here: :mod:`~bookmarks.maya.plugin`.


    .. grid-item-card::

        **ShotGrid / FFMpeg / RV**
        ^^^

        Bookmark and asset items can be linked with ShotGrid entities.
        The current ShotGrid help functions are defined in :mod:`~bookmarks.shotgun`.

        Bookmarks can also make use of ffmpeg to convert image sequences to movies, per
        the :mod:`~bookmarks.external.ffmpeg` module.



.. toctree::
    :maxdepth: 1
    :hidden:
    :glob:

    modules/*



