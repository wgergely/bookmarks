<p align="center">
  <img width="200" src="https://bookmarks-vfx.com/_static/icon.png">
  <img width="480" src="https://bookmarks-vfx.com/_images/active_bookmark.png">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-lightgrey">
  <img src="https://img.shields.io/badge/Python-PySide2-lightgrey">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey">
  <img src="https://img.shields.io/badge/Version-v0.8.0-green">
</p> 

<p align="center">
    ☺  Bookmarks is a free, open-source utility that helps you organize and prepare assets
    for digital productions. With Bookmarks, you can easily create folders for new jobs and assets
    using templates, parse and read existing jobs and assets, sort and filter items,
    and annotate them with notes.
    Whether you're working on a film, TV show, or other digital production,
    Bookmarks can help you save time and stay organized.
</p>

---


[`User Guide`](https://bookmarks-vfx.com/guide.html#user-guide)  |  [`Python Modules`](https://bookmarks-vfx.com/modules.html#python-modules)  |  [`Get Bookmarks`](https://bookmarks-vfx.com/guide.html#get-bookmarks)

---

# Features

The app categorises  project content as separate [`bookmarks`](https://bookmarks-vfx.com/modules/items/bookmark_items.html#module-bookmarks.items.bookmark_items),
[`assets`](https://bookmarks-vfx.com/modules/items/asset_items.html#module-bookmarks.items.asset_items) and [`file items`](https://bookmarks-vfx.com/modules/items/file_items.html#module-bookmarks.items.file_items).
You can configure these independently to link with, for instance, ShotGrid entities or
configure their properties like frame rate and resolution to set [`Maya scene settings`](https://bookmarks-vfx.com/modules/maya/plugin.html#module-bookmarks.maya.plugin).
You can use filters to sort and hide items, preview images, convert footage sequences, or ‘publish’ files.
See [User Guide](https://bookmarks-vfx.com/guide.html#user-guide) for more information.

# About

I developed the app to help manage personal projects and keep [`myself`](https://gergely-wootsch.com) organised (I’m a digitally messy person!). So, whilst it works great for me, it might not be best suited for you. Still, I tried to make it easily customisable to help adapt to site-specific environments. See the [`Python Modules`](https://bookmarks-vfx.com/modules.html#python-modules) page for more information.

# Dependencies

The release contains all Windows dependencies. For setting up a custom development environment on another platform, you’ll need the following python dependencies:


* [Python3](https://github.com/python/cpython) -  Tested against 3.9


* [PySide2](https://pypi.org/project/PySide2) - Tested against Qt 5.15.2


* [OpenImageIO](https://github.com/OpenImageIO/oiio) - Tested against 2.3


* [numpy](https://pypi.org/project/numpy)


* [slack_sdk](https://pypi.org/project/slack_sdk)


* [psutil](https://pypi.org/project/psutil)


* [shotgun_api3](https://github.com/shotgunsoftware/python-api)

<!-- note:

* Currently, Windows is the only supported platform (although much of the codebase should be platform-agnostic).
* OpenImageIO does not currently maintain installable python packages. -->
