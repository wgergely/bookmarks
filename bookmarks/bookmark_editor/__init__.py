# -*- coding: utf-8 -*-
"""Bookmark editor module.

This module is responsible for adding server locations, creating job folders,
and listing existing ``bookmark`` items. Whilst these are very much site-specific tasks
- e.g. studios usually use a database to store information about jobs and clients -
Bookmarks tries to parse folder structures at a given ``server`` path and look for
existing bookmark items inside these jobs.

Note: Physically parsing a big project structure takes a long time, thus this
module in its current form is not very optimised.

"""
