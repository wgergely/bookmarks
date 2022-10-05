"""When a bookmark item is set up with a Microsoft Teams Incoming Webhook URL,
we can use it to send cards (messages) to the associated channel. The current
functionality is limited and is currently only used to signal new publishes.

"""

import json

import requests
from PySide2 import QtGui, QtCore

from .. import common
from .. import images

PUBLISH_MESSAGE = {
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "type": "AdaptiveCard",
                "body": [
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "isSubtle": True,
                                        "text": "Asset",
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "Type",
                                        "isSubtle": True,
                                        "horizontalAlignment": "Left",
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "User",
                                        "isSubtle": True,
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "Date",
                                        "isSubtle": True,
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "Path",
                                        "isSubtle": True,
                                        "horizontalAlignment": "Left",
                                    },
                                ],
                                "verticalContentAlignment": "Top",
                                "horizontalAlignment": "Left",
                                "width": "auto"
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "verticalContentAlignment": "Top",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "<ASSET>",
                                        "weight": "Bolder",
                                        "horizontalAlignment": "Left",
                                        "wrap": True
                                    },
                                    {
                                        "type": "TextBlock",
                                        "horizontalAlignment": "Left",
                                        "text": "<TASK>",
                                        "wrap": True
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "<USER>",
                                        "horizontalAlignment": "Left",
                                        "wrap": True,
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "<DATE>",
                                        "horizontalAlignment": "Left",
                                        "wrap": True,
                                    },
                                    {
                                        "type": "TextBlock",
                                        "horizontalAlignment": "Left",
                                        "text": "<PATH>",
                                        "wrap": True
                                    },
                                ],
                            }
                        ],
                        "horizontalAlignment": "Center"
                    },
                    {
                        "type": "Image",
                        "url": "data:image/png;base64,<IMAGE>"
                    }
                ],
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.2",
                "verticalContentAlignment": "Top"
            }
        }
    ]
}


def send(webhook, payload):
    """Send the specified payload using the given webhook.

    Args:
        webhook (str): The URL of the webhook.
        payload (str): The payload to send.

    """
    response = requests.post(
        webhook,
        json=payload,
        headers={"Content-Type": "application/json"},
        proxies={},
        timeout=60,
        verify=None,
    )

    if response.status_code == requests.codes.ok and response.text == '1':
        return True
    else:
        raise RuntimeError(response.text)


def get_payload(
        card,
        thumbnail=None,
        asset='',
        publish_type='',
        path='',
        date='',
        user=common.get_username(),
):
    """Get a formatted payload to send.

    Returns:
        dict: The payload data as a dictionary.

    """
    image = QtGui.QImage(thumbnail)
    image = images.ImageCache.resize_image(image, 256)

    ba = QtCore.QByteArray()
    buffer = QtCore.QBuffer(ba)
    buffer.open(QtCore.QIODevice.WriteOnly)
    image.save(buffer, 'PNG')
    base64_data = ba.toBase64().data().decode('utf-8')

    data = json.dumps(card)
    data = data. \
        replace('<IMAGE>', base64_data). \
        replace('<TASK>', publish_type). \
        replace('<ASSET>', asset). \
        replace('<PATH>', path). \
        replace('<USER>', user). \
        replace('<DATE>', date)

    return json.loads(data)
