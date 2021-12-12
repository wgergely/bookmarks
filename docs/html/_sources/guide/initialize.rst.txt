Running Bookmarks
=================

Downloaded the latest release, and install it. See this quick setup guide for more
information.

You can also run Bookmarks from a Python console. See this guide for a quick guide.

To do so it has to be initialized in :attr:`bookmarks.common.StandaloneMode` or

``embedded`` mode. To start the ``standalone`` app, simply call :func:`bookmarks.exec_`:


.. code-block:: python

    import bookmarks
    bookmarks.exec_()


To run it from a host application, you'll have to first initialize in ``EmbeddedMode``:

.. code-block:: python

    from bookmarks import common
    common.initialize(common.EmbeddedMode)

