# -*- coding: utf-8 -*-
"""Online version checking mechanism.

Version control is implemented using GitHub's REST API.

Copyright (C) 2021 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""

from __future__ import absolute_import, division
import subprocess
import os
import urllib2
import json
import socket

from PySide2 import QtWidgets, QtCore

from . import version
from .. import log
from .. import common
from .. import ui
from .. import actions
from .. import __version__ as package_version


URL = u'https://api.github.com/repos/wgergely/bookmarks/releases'
socket.setdefaulttimeout(5)

responses = {
    100: ('Continue', 'Request received, please continue'),
    101: ('Switching Protocols',
          'Switching to new protocol; obey Upgrade header'),

    200: ('OK', 'Request fulfilled, document follows'),
    201: ('Created', 'Document created, URL follows'),
    202: ('Accepted',
          'Request accepted, processing continues off-line'),
    203: ('Non-Authoritative Information', 'Request fulfilled from cache'),
    204: ('No Content', 'Request fulfilled, nothing follows'),
    205: ('Reset Content', 'Clear input form for further input.'),
    206: ('Partial Content', 'Partial content follows.'),

    300: ('Multiple Choices',
          'Object has several resources -- see URI list'),
    301: ('Moved Permanently', 'Object moved permanently -- see URI list'),
    302: ('Found', 'Object moved temporarily -- see URI list'),
    303: ('See Other', 'Object moved -- see Method and URL list'),
    304: ('Not Modified',
          'Document has not changed since given time'),
    305: ('Use Proxy',
          'You must use proxy specified in Location to access this '
          'resource.'),
    307: ('Temporary Redirect',
          'Object moved temporarily -- see URI list'),

    400: ('Bad Request',
          'Bad request syntax or unsupported method'),
    401: ('Unauthorized',
          'No permission -- see authorization schemes'),
    402: ('Payment Required',
          'No payment -- see charging schemes'),
    403: ('Forbidden',
          'Request forbidden -- authorization will not help'),
    404: ('Not Found', 'Nothing matches the given URI'),
    405: ('Method Not Allowed',
          'Specified method is invalid for this server.'),
    406: ('Not Acceptable', 'URI not available in preferred format.'),
    407: ('Proxy Authentication Required', 'You must authenticate with '
          'this proxy before proceeding.'),
    408: ('Request Timeout', 'Request timed out; try again later.'),
    409: ('Conflict', 'Request conflict.'),
    410: ('Gone',
          'URI no longer exists and has been permanently removed.'),
    411: ('Length Required', 'Client must specify Content-Length.'),
    412: ('Precondition Failed', 'Precondition in headers is false.'),
    413: ('Request Entity Too Large', 'Entity is too large.'),
    414: ('Request-URI Too Long', 'URI is too long.'),
    415: ('Unsupported Media Type', 'Entity body in unsupported format.'),
    416: ('Requested Range Not Satisfiable',
          'Cannot satisfy request range.'),
    417: ('Expectation Failed',
          'Expect condition could not be satisfied.'),

    500: ('Internal Server Error', 'Server got itself in trouble'),
    501: ('Not Implemented',
          'Server does not support this operation'),
    502: ('Bad Gateway', 'Invalid responses from another server/proxy.'),
    503: ('Service Unavailable',
          'The server cannot process the request due to a high load'),
    504: ('Gateway Timeout',
          'The gateway server did not receive a timely response'),
    505: ('HTTP Version Not Supported', 'Cannot fulfill request.'),
}



@common.error
@common.debug
def check():
    """Checks the latest release tag on Github and compares it with the current
    version number.

    """

    # First let's check if there's a valid internet connection
    try:
        r = urllib2.urlopen(u'http://google.com', timeout=5)
    except urllib2.URLError:
        raise
    except socket.timeout:
        raise

    try:
        r = urllib2.urlopen(URL, timeout=5)
        data = r.read()
    except urllib2.URLError as err:
        raise
    except socket.timeout as err:
        raise
    except RuntimeError as err:
        raise

    code = r.getcode()
    if not (200 <= code <= 300):
        s = u'# Error {}. "{}" {}'.format(
            code, URL, responses[code])
        raise RuntimeError(s)

    # Convert json to dict
    try:
        data = json.loads(data)
    except Exception as err:
        s = u'Error occured loading the server response: {} "{}" {}'.format(
            code, URL, responses[code])
        raise RuntimeError(s)

    tags = [(version.parse(f[u'tag_name']).release, f) for f in data]
    if not tags:
        ui.MessageBox(
            u'No versions are available',
            u'Could not find any releases. Maybe no release has been published yet for this product?'
        ).open()
        return

    # Getting the latest version
    latest = max(tags, key=lambda x: x[0])
    current_version = version.parse(package_version)
    latest_version = version.parse(latest[1][u'tag_name'])

    # We're good and there's not need to update
    if current_version >= latest_version:
        ui.OkBox(
            u'You\'re running the latest version of {}'.format(common.PRODUCT),
        ).open()
        return

    mbox = QtWidgets.QMessageBox()
    mbox.setWindowTitle(u'A new update is available')
    mbox.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    mbox.setStandardButtons(
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    mbox.setText(u'There is a new version of Bookmarks available.')
    mbox.setText(
        u'Your current version is {} and the latest available version is {}.\nDo you want to download the new version?'.format(current_version, latest_version))
    res = mbox.exec_()

    if res == QtWidgets.QMessageBox.No:
        return

    # Getting the packages...
    downloads_folder = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.DownloadLocation)

    progress_widget = QtWidgets.QProgressDialog(
        u'Downloading installer...', u'Cancel download', 0, 0)
    progress_widget.setWindowTitle(u'Downloading...')
    progress_widget.setWindowFlags(QtCore.Qt.FramelessWindowHint)

    # On windows, we will download the asset to the user downloads folder
    if common.get_platform() == common.PlatformWindows:
        asset = next(
            (f for f in latest[1][u'assets'] if f[u'name'].endswith(u'exe')), None)
    elif common.get_platform() == common.PlatformMacOS:
        asset = next(
            (f for f in latest[1][u'assets'] if f[u'name'].endswith(u'zip')), None)
    elif common.get_platform() == common.PlatformUnsupported:
        raise NotImplementedError('Not yet implemented on this platform.')
    else:
        raise ValueError('Invalid platform value')

    # We will check if a file exists already...
    file_info = QtCore.QFileInfo(
        u'{}/{}'.format(downloads_folder, asset['name']))
    _file_info = file_info

    # Rename our download if the file exists already
    idx = 0
    while _file_info.exists():
        idx += 1
        _file_info = QtCore.QFileInfo(
            u'{}/{} ({}).{}'.format(
                file_info.path(),
                file_info.completeBaseName(),
                idx,
                file_info.completeSuffix(),
            )
        )
    file_info = _file_info
    file_path = os.path.abspath(os.path.normpath(file_info.absoluteFilePath()))

    with open(file_path, 'wb') as f:
        response = urllib2.urlopen(asset[u'browser_download_url'], timeout=5)
        total_length = response.headers['content-length']

        if total_length is None:  # no content length header
            progress_widget.setMaximum(0)
            progress_widget.forceShow()
            QtWidgets.QApplication.instance().processEvents()
            f.write(response.content)
            progress_widget.close()
            return
        else:
            progress_widget.setMaximum(100)

        current_length = 0
        progress_widget.forceShow()

        while True:
            QtWidgets.QApplication.instance().processEvents()
            data = response.read(4096)
            if not data:
                break
            if not progress_widget.wasCanceled():
                current_length += len(data)
                f.write(data)
                progress_widget.setValue(
                    (float(current_length) / float(total_length)) * 100)
            else:
                f.close()
                if os.path.exists(file_path):
                    os.remove(file_path)

    if not progress_widget.wasCanceled():
        cmd = u'"{}"'.format(file_path)
        subprocess.Popen(cmd)
        actions.reveal(file_path)

    progress_widget.close()
    progress_widget.deleteLater()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    check()
