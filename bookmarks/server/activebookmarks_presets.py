"""This module implements a simple API for managing active bookmarks presets.

The presets are json files that contain a snapshot of the current active bookmarks items.
The preset file is an array of objects. Each object is structured in the following way:

.. code-block:: json

    [
        {
            "name": "Preset 1",
            "server": "//my-server.local/jobs",
            "jobs": "my-client/my-job",
            "root": "data/shots"
        },
        {
            "name": "Preset 2",
            "server": "//my-server.local/jobs",
            "jobs": "my-client/my-job",
            "root": "data/assets"
        },
        {
            ...
        }
    ]


"""
import os
import json

from .. import common
from .. import log
from . import lib

PRESETS_DIR = f'{common.temp_path()}/bookmark_presets'
api = None


def _init_active_bookmark_presets():
    if not os.path.exists(PRESETS_DIR):
        os.makedirs(PRESETS_DIR)
        log.debug(__name__, f'Created directory: {PRESETS_DIR}')

    global api
    if api is None:
        api = ActiveBookmarksPresetsAPI()

    if not isinstance(api, ActiveBookmarksPresetsAPI):
        raise TypeError('API must be an instance of ActiveBookmarksPresetsAPI')

    return api


class ActiveBookmarksPresetsAPI:

    def __init__(self):
        #: A local cache of the presets
        self._presets = {}

    def _verify_preset(self, preset):

    # to implement

    def _get_preset_by_name(self, preset_name):

    # to implement

    def preset_to_path(self, preset_name):
        """Returns the bookmark's key (path) value for a given preset name."""
        # f'{server}/{jobs}/{root}'

    def get_presets(self, force=False):
        """Return the list of presets saved to disk."""
        if not force and self._presets:
            return self._presets

    def import_preset(self, preset_name, source_file):
        """Import a preset from a file."""

    def export_preset(self, preset_name, destination_file):
        """Export a preset to a file."""

    def save_preset(self, preset_name, data):
        """Save a preset to disk."""

    def delete_preset(self, preset_name):
        """Delete a preset from disk."""

    def activate_preset(self, preset_name):
        """Set the contents of the preset as the current active bookmarks set."""

    def clear_presets(self):
        """Delete all presets from disk."""

    def is_valid(self, preset_name):
        """Check if a preset is valid."""

    def rename_preset(self, old_name, new_name):
        """Rename a preset."""
