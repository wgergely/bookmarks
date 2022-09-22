Core Modules
============

The core modules define basic functionality used throughout the app.

:mod:`bookmarks.common` is a mishmash of utility classes and functions that define how
Bookmarks is loads resources, custom fonts, data caches, user settings, internal app signals, etc.

:mod:`bookmarks.database` is define the bookmark item database interface.

:mod:`bookmarks.images` module contains the image cache used to store resources and thumbnails
and other OpenImageIO related functions.


.. toctree::
    :maxdepth: 3

    Common <api/common>
    Database <api/database>
    Images <api/images>
    Threads <api/threads>
    Tokens <api/tokens>
