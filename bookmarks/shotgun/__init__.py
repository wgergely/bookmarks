"""ShotGrid integration modules, classes and utility functions.

Bookmark and asset items can be linked with their ShotGrid counterparts. The linkage
information is stored in the bookmark item database.

Check the :mod:`¬bookmarks.shotgun.shotgun` contains the generic entity model, and
a utility class used to collect locally set ShotGrid configuration data -
:mod:`~bookmarks.shotgun.shotgun.ShotgunProperties`.

I've also included an experimental publish script, but it was not tested.

Note:
    This module unfortunately is not well maintained. Still, in principle, as long as the
    ShotGrid python API stays consistent most functionality here is quasi-functional.

"""
