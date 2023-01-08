.. meta::
    :description: Documentation page for Bookmarks, a free and open-source Python asset manager for film, animation and VFX projects.
    :keywords: Bookmarks, bookmarksvfx, asset manager, assets, PySide, Qt5, PySide2, Python, vfx, animation, film, productivity, free, open-source, opensource, lightweight, ShotGrid, RV, FFMpeg, ffmpeg, publish, manage, digital content management, production, OpenImageIO
    :google-site-verification: y51rSjHP3kvSHILPGb_k7cu8E5yNJ_XyRQ0eGwIqy2M


.. centered:: |logo| |image1|

.. centered:: |label1| |label2| |label3| |label4|

------------

.. centered:: :ref:`User Guide`  |  :ref:`Python Modules`  |  :ref:`Get Bookmarks`

------------


Welcome
-----------

Bookmarks is a free, open-source utility that simplifies the process of organizing and preparing assets for digital productions. With Bookmarks, you can quickly create new jobs and assets using templates, parse and read existing jobs and assets, and sort and filter items with ease. Additionally, you can annotate items with notes to help keep track of important information. Bookmarks can be a valuable tool for anyone working on a film, TV show, or other digital production, as it helps save time and keep your workflows organized.


Features
**************


The app categorises  project content as separate :mod:`bookmarks<bookmarks.items.bookmark_items>`,
:mod:`assets<bookmarks.items.asset_items>` and :mod:`file items<bookmarks.items.file_items>`.
You can configure these independently to link with, for instance, ShotGrid entities or
configure their properties like frame rate and resolution to set :mod:`Maya scene settings <bookmarks.maya.plugin>`.
You can use filters to sort and hide items, preview images, convert footage sequences, or 'publish' files.

See the :ref:`User Guide` for more information.



Quick Start
***************

To start using Bookmarks :ref:`download and install the latest version <Get Bookmarks>`.

For running the Python module, the simplest way to start Bookmarks as a standalone PySide application is:

.. code-block:: python
    :linenos:

    import bookmarks
    bookmarks.exec_()

Please see  :ref:`Python Modules` for more information.


About Bookmarks
***************

I developed the app to help manage personal projects and keep myself organised (I'm a digitally messy person!). So, whilst it works great for me, might not be useful for you. Still, I tried to make it easily customisable to help adapt to site-specific environments. The :ref:`Python Modules` has all the information if you'd like to make changes.


.. |logo| image:: _static/icon.png
   :height: 200
   :width: 200
   :alt: Bookmarks - Lightweight asset manager designed for VFX, animation, film productions

.. |label1| image:: https://img.shields.io/badge/Python-3.8%2B-lightgrey
   :height: 18

.. |label2| image:: https://img.shields.io/badge/Python-PySide2-lightgrey
   :height: 18

.. |label3| image:: https://img.shields.io/badge/Platform-Windows-lightgrey
   :height: 18

.. |label4| image:: https://img.shields.io/badge/Version-v0.7.4-green
   :height: 18

.. |image1| image:: ./images/active_bookmark.png
    :width: 480







.. toctree::
    :maxdepth: 3
    :hidden:

    guide


.. toctree::
    :maxdepth: 2
    :hidden:
    :caption: Technical Documentation

    modules
    modindex


.. codeauthor:: Gergely Wootsch <hello@gergely-wootsch.com>

.. sectionauthor:: Gergely Wootsch <hello@gergely-wootsch>


.. toctree::
    :hidden:
    :caption: Project Links

    GitHub <https://github.com/wgergely/bookmarks>
    License <license>




