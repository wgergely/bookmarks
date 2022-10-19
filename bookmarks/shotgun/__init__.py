"""ShotGrid integration modules, classes and utility functions.

Bookmark and asset items can be linked with their ShotGrid counterparts. The linkage
information is stored in the bookmark item database. The utility methods allow getting
and setting some basic information in Bookmarks and ShotGrid to synchronize cut data,
thumbnails, descriptions.

I've also included an experimental publish script, but it was not tested.

Note:
    This module unfortunately is not well maintained. Still, in principle, as long as the
    ShotGrid python API stays consistent most functionality here is quasi-functional.

"""
