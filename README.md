### Python-based asset manager to locate, annotate and browse project content.

<br>

![alt text](https://img.shields.io/badge/Python-2.7-lightgrey.svg "Python 2.7") ![alt text](https://img.shields.io/badge/Qt-5.6%2B-lightgrey.svg "Qt 5.6+") ![alt text](https://img.shields.io/badge/platform-windows-lightgray.svg "Windows")
<br>


### [Download installer (Windows only)](https://github.com/wgergely/bookmarks/releases)

***

<br>

Bookmarks is a lightweight asset manager designed to browse film, animation or VFX project content. It utilises the brilliant OpenImageIO library to generate thumbnails. It also provides a simple interface to create jobs based on zip template files and various tools to annotate and filter items.

Use Bookmarks to separate larger project folder structures into smaller logical parts. We refer to these parts as bookmark items. For example, `{job}/SHOTS` or `{jobs}/ASSETS` folders could be considered bookmark items and contain framerate, resolution, Slack and Shotgun connection information. Use these properties to link assets with their Shotgun counterparts, send Slack messages or apply cut and resolution settings to Maya scenes.

<a href="./bookmarks/rsc/docs/bookmark_graph.jpg" target="_blank">Content is organised into 3 tabs: bookmark items, assets and files:</a>
Bookmarks are arbitrary folders inside a job and contain asset items.
_Assets_ are Maya workspace-like folder structures and contain a
series of subfolders (think _scene_, _render_, _cache_ folders).
_Files_ are project and image files stored in asset subfolders. The tool lists all files in the selected asset subfolder - the idea here is that this provides a good overview to then use the provided search and filter tools to locate project and image files. 

Maya
----

Bookmarks started out as a Maya utility and we're still providing a Maya plugin. It replaces the internal Maya Project Manager and uses the current asset for setting the Workspace. Bookmarks also boundles a few utility scripts for importing/exporting scenes and file caches, capturing viewport, and more!


Dependencies
------------

Bookmarks is a Python2 project tested against PySide2 / Qt5. We're using the python bindings of [OpenImageIO](https://github.com/OpenImageIO/oiio), [Alembic](https://github.com/alembic/alembic) and the [shotgun_api3](https://github.com/shotgunsoftware/python-api), [psutil](https://github.com/giampaolo/psutil), slackclient and [scandir](https://github.com/benhoyt/scandir) modules. Currently only we're only packaging Bookmarks with precompiled dependecies for Windows, but Bookmarks should be able to run on other platforms. Some functionaly is not platform agnostic and has not yet been implemented.


Usage
-----

If all the dependecies are satisfied, you can start Bookmarks calling its exec method:

```python
import bookmarks
bookmarks.exec_()
```
To start bookmarks in Maya best is to use the boundled Maya plugin. The installer will automatically install the plugin if a Maya installation is available on your system. Otherwise, the source plugin code can be found at `./bookmarks/maya/plugin.py`.
