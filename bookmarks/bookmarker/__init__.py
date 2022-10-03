"""This module defines the widgets needed to allow the user to select and create
bookmark items.

This requires specifying servers, creating job folders, and letting the user pick
existing folders to be used as bookmark items.

See :class:`~bookmarks.bookmarker.main.BookmarkerWidget`,
:class:`~bookmarks.bookmarker.server_editor.ServerItemEditor`,
:class:`~bookmarks.bookmarker.job_editor.JobItemEditor`,
and :class:`~bookmarks.bookmarker.bookmark_editor.BookmarkItemEditor` for more
information.


To show the main editor call:

.. code-block:: python
    :linenos:

    import bookmarks.actions
    bookmarks.actions.show_bookmarker()


"""
