"""This Python module provides functionality for interacting with ShotGrid.

The module encompasses a range of ShotGrid operations, including:

* Linking assets or bookmarks to entities.
* Showing task pickers and link assets.
* Publishing and uploading thumbnails to ShotGrid.
* Testing the ShotGrid connection.
* Creating new ShotGrid entities and projects.
* Saving entity data to a database.
* Retrieving status codes available in the current context.
* Creating and verifying published file versions.
* Uploading thumbnails.


Bookmark and asset items m,ust be linked with their ShotGrid entities. The linkage
information is stored in the bookmark item database.

:mod:`¬bookmarks.shotgun.shotgun` contains the generic entity model, and
a utility class used to collect locally set ShotGrid configuration data -
:mod:`~bookmarks.shotgun.shotgun.SGProperties`.

"""
