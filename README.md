<p align="center">
  <img width="300" height="300" src="https://github.com/wgergely/bookmarks/blob/main/bookmarks/rsc/gui/icon.png?raw=true">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-lightgrey">
  <img src="https://img.shields.io/badge/Python-PySide2-lightgrey">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey">
  <img src="https://img.shields.io/badge/Version-v0.6.0-green">
</p> 

<p align="center">
  Bookmarks is a lightweight Python asset manager designed to browse and manage content of animation, VFX and film projects.<br>
  https://github.com/wgergely/bookmarks/releases/download/0.6.0/Bookmarks_0.6.0.exe
</p>

---

### Features

Bookmarks separate content as `bookmark`, `asset` and `file` items. Each
bookmark item contains a series of asset items that in turn contain the file
items. Bookmark and asset items can be configured independently to link with,
for instance, `ShotGrid` entities or be set up with properties, like frame-rate,
resolution, and custom URLs. These properties can be used to quickly configure scenes
in host applications, e.g. Maya, and to access related external resources.



The app provides simple tools to create jobs and assets using ZIP templates, templated file-names
and options to annotate and filter existing items, and preview images using `OpenImageIO`.

### Background

This project was developed to manage personal projects and is adapted to
custom way of setting them up. his is to say, Bookmarks expects certain patterns to
be respected to read files and folders correctly. I tried my best to keep things
customizable to adapt to site specific environments.

<p align="center">
  <img src="https://github.com/wgergely/bookmarks/blob/main/docs/media/bookmarks.gif?raw=True">
</p>

### Quick Start

The simplest way to start Bookmarks as a standalone application is to run:

```python
import bookmarks
bookmarks.exec_()
```

### Dependencies

The following python packages are required to run Bookmarks:


* `Python3`: Tested against 3.9.


* `PySide2`: Tested against Qt 5.15.2. [https://pypi.org/project/PySide2](https://pypi.org/project/PySide2)


* `OpenImageIO`: Used to generate thumbnails for image items [https://github.com/OpenImageIO/oiio](https://github.com/OpenImageIO/oiio)


* `numpy`: [https://pypi.org/project/numpy](https://pypi.org/project/numpy)


* `slack_sdk`: [https://pypi.org/project/slack_sdk](https://pypi.org/project/slack_sdk)


* `psutil`: [https://pypi.org/project/psutil](https://pypi.org/project/psutil)


* `shotgun_api3`: [https://github.com/shotgunsoftware/python-api](https://github.com/shotgunsoftware/python-api)

Currently, Windows is the only supported platform (although much of the codebase should
be platform-agnostic).

**NOTE**: OpenImageIO does not currently maintain installable python packages. Building it
manually is therefore required.

### Standalone and Embedded Modes

Bookmarks can be run in two modes. As a standalone application, or embedded in a
PySide2 environment. The base-layers can be initialized with:

```python
from bookmarks import common
common.initialize(common.EmbeddedMode) # or common.StandaloneMode
```

[`bookmarks.exec_()`](api/main.md#bookmarks.exec_) is a utility method for starting Bookmarks in
`common.StandaloneMode`, whilst `common.EmbeddedMode` is useful when
running from inside a host DCC. Currently only the Maya plugin makes use of this mode.
See `bookmarks.maya` and [`bookmarks.common`](api/common.md#module-bookmarks.common) for the related methods.


## Python Modules Documentation

https://bookmarks.gergely-wootsch.com/html/api.html

