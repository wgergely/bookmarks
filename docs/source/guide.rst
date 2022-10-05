==============
User Guide
==============


Read time: 3 minutes. If you're looking for the python module documentation, it's here:
:ref:`Python Modules`.



What is this, and why does it exist?
----------------------------------------

.. centered:: |active_bookmark|

Bookmarks is a simple asset manager for film, animation and VFX projects. It is free and open-source.

It can be a local hub for accessing assets and files and connecting them with external resources, such as ShotGrid entities and URLs, or a place for notes and comments.

It helps me (the author) create jobs and assets and keep scene files named neat and consistent!


.. |active_bookmark| image:: images/active_bookmark.png



Download
-------------------------

Download and install the latest release from `github <https://github.com/wgergely/bookmarks/releases>`_:

.. admonition:: Latest Windows Release

    `Bookmarks v0.7.0 <https://github.com/wgergely/bookmarks/releases/download/0.7.0/Bookmarks_0.7.0.exe>`_.



I have an issue or question
----------------------------------------------

The best place to report bugs, errors, and feature requests is on github.

`Github Issue Tracker <https://github.com/wgergely/bookmarks/issues>`_

Contact the author:

`E-mail <mailto:%22Gergely%20Wootsch%22%3chello@gergely-wootsch.com%3e?subject=%5BBookmarks%5D>`_

`Twitter <https://twitter.com/wgergely>`_


How does it work?
-------------------------

The app breaks down projects into separate **bookmark** items. These are simply folders inside a job, like the 'scenes' or 'asset' folders, where production content usually resides.

Bookmark items are comprised of 'server', 'job' and 'root' parts, for example:

    ``//server/jobs/project_0010/path/to/shots_folder`` is a bookmark item, where **//server/jobs** is the server, **project_0010** is the job and **path/to/shots_folder** is the root folder.

The app will use the bookmark items to look for assets and the assets to look for files. These items are shown in their own separate tabs:


.. centered:: |window_tabs|


.. |window_tabs| image:: images/window_tabs.png


How do I use it?
--------------------


Let's set a demo project up from scratch and create a template file to be used as a naming reference for an After Effects scene file.


1. Add bookmark items
*************************

First, let's create a new job called **DEMO**. With the Bookmarks tab active, right-click and select 'Add/Remove bookmark items...'.


.. carousel::
    :data-bs-keyboard: true
    :data-bs-wrap: true
    :data-bs-touch: true
    :data-bs-pause: hover
    :data-bs-interval: false
    :show_controls:
    :no_fade:

    .. image:: images/bookmark_add.png
    .. image:: images/job_add.png


1.1. Add a server
####################

Click the green add icon to add a new server. A server is usually a network location, but we can add **C:/jobs** - make sure the folder exists!

1.2. Add a job
#################

Select **C:/jobs** and create a new job by clicking the green plus icon in the middle section. Name it **DEMO** and select the 'Job' template and click 'Add Job'.

.. hint::

	You can add custom templates by dragging a zip file containing your job template onto the item selector.

1.3. Add bookmark item
######################

You should see a list of root folders appear in the right column. Add them by double-clicking.
Close the editor.


2. Add asset
*****************

Next, let's make a new asset called **DEMO_ASSET**. Double-click 'data/asset' in the main app window to 'activate' it. This will show
the Assets tab and the bookmark item's contents. Right-click on the window and select 'Add Asset...'.

.. carousel::
    :data-bs-keyboard: true
    :data-bs-wrap: true
    :data-bs-touch: true
    :data-bs-pause: hover
    :data-bs-interval: false
    :show_controls:
    :no_fade:

    .. image:: images/active_bookmark.png
    .. image:: images/asset_add.png


Enter the name, select the 'Asset' template and click 'Add asset'.
Select **DEMO_ASSET** and press enter (or double-click it). This will reveal the file contents of the asset.


.. hint::

	You can create sequences and shots in the exact same manner using 'SEQ###' and 'SH####' naming, e.g. SEQ010_SH0010. Unfortunately, the app doesn't support nesting asset folders like 'SEQ010/SH0010'.


3. Add a template file
************************


.. carousel::
    :data-bs-keyboard: true
    :data-bs-wrap: true
    :data-bs-touch: true
    :data-bs-pause: hover
    :data-bs-interval: false
    :show_controls:
    :no_fade:

    .. image:: images/asset_item.png
    .. image:: images/file_add.png
    .. image:: images/file_saver.png



Right-click again and select 'Add File...'. This will reveal a file saver. Set Template to 'Asset Scene Task', the 'Task' to 'comp' and the 'Format' to 'aep'.

We omitted to set the project prefix up earlier, so click the Project Prefix 'Edit' button and set it to 'DP' for Demo Project. That's all. Hit 'Save' to create an empty template file that can be used for naming reference.


.. hint::

    I tend to copy the template file's path (there's a Copy context menu or press CTRL+C) to later paste it when saving a file from After Effects. This lets me skip having to navigate folders.

.. note:: Reading files

    There's a little gotcha: we read file items from the assets' subfolders (or *task folders*), not from the asset folder directly.
    Pick the current *task folder* by clicking the 'Files' tab button or right-clicking the window and selecting 'Select Task Folder...'. This will list all files and folders inside that task folder.


Configuring bookmark and asset items
--------------------------------------------

You can edit basic properties, like external URLs, frame rate, file-filter rules, width, and height attributes. Click the settings icon or press CTRL+E to open an item's properties editor.

The properties will help create footage 'publishes', convert image sequences, and, using the Maya plugin, set the Maya workspace and scene settings. Linking URLs and ShotGrid entities with local files can be beneficial when the project has a lot of external resources to keep track of.


Filters
--------------------

You can sort and filter the item using the buttons on the top bar and the options in the context menus. The label-like item names are clickable: use the 'shift' and 'alt' keyboard modifiers when clicking them to toggle filters.
