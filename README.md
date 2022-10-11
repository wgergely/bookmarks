<p align="center">
  <img width="200" src="https://bookmarks.gergely-wootsch.com/html/_static/icon.png">
  <img width="480" src="https://bookmarks.gergely-wootsch.com/html/_images/active_bookmark.png">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-lightgrey">
  <img src="https://img.shields.io/badge/Python-PySide2-lightgrey">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey">
  <img src="https://img.shields.io/badge/Version-v0.7.3-green">
</p> 

<p align="center">
  ☺  Bookmarks is a free and open-source Python asset manager designed to browse and manage the content of animation, VFX and film projects.
</p>

---


[`User Guide`](https://bookmarks.gergely-wootsch.com/html/guide.html#user-guide)  |  [`Python Modules`](https://bookmarks.gergely-wootsch.com/html/modules.html#python-modules)  |  [`Get Bookmarks`](https://bookmarks.gergely-wootsch.com/html/guide.html#get-bookmarks)

---

# Features

The app categorises  project content as separate [`bookmarks`](https://bookmarks.gergely-wootsch.com/html/modules/items/bookmark_items.html#module-bookmarks.items.bookmark_items),
[`assets`](https://bookmarks.gergely-wootsch.com/html/modules/items/asset_items.html#module-bookmarks.items.asset_items) and [`file items`](https://bookmarks.gergely-wootsch.com/html/modules/items/file_items.html#module-bookmarks.items.file_items).
You can configure these independently to link with, for instance, ShotGrid entities or
configure their properties like frame rate and resolution to set [`Maya scene settings`](https://bookmarks.gergely-wootsch.com/html/modules/maya/plugin.html#module-bookmarks.maya.plugin).
You can use filters to sort and hide items, preview images, convert footage sequences, or ‘publish’ files.
See [User Guide](https://bookmarks.gergely-wootsch.com/html/guide.html#user-guide) for more information.

# Background

I developed the app to help manage personal projects and keep myself organised (I’m a digitally messy person). So, whilst it works great for me, it might not work for you. Still, I tried to make it easily customisable to help adapt to site-specific environments. See the python modules documentation for more information.

# Quick Start

The simplest way to start Bookmarks as a standalone application is to run:

```python
import bookmarks
bookmarks.exec_()
```

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
