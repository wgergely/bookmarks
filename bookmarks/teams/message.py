"""Microsoft Teams API integration module.

When a bookmark item is set up with a Microsoft Teams Incoming Webhook URL,
we can use it to send cards (messages) to the associated channel. The current
functionality is limited and is currently only used to signal new publishes.

"""

import os
import json
import base64

import requests

from .. import images
from .. import common


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
                        "type": "TextBlock",
                        "text": "Publish",
                        "fontType": "Default",
                        "size": "Large",
                        "weight": "Bolder",
                        "spacing": "Large"
                    },
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "isSubtle": True,
                                        "horizontalAlignment": "Left",
                                        "text": "Shot"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "Type",
                                        "isSubtle": True,
                                        "horizontalAlignment": "Left",
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "Path",
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
                                    }
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
                                        "text": "<SEQ>_<SHOT>",
                                        "weight": "Bolder",
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "horizontalAlignment": "Left",
                                        "text": "<TYPE>"
                                    },
                                    {
                                        "type": "RichTextBlock",
                                        "inlines": [
                                            {
                                                "type": "TextRun",
                                                "text": "<PATH>"
                                            }
                                        ]
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "<USER>",
                                        "horizontalAlignment": "Left"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": "<DATE>",
                                        "horizontalAlignment": "Left"
                                    }
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
                "version": "1.3",
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
        seq='SEQ###',
        shot='SH###',
        publish_type='',
        path='',
        date='',
        user=common.get_username(),
):
    """Get a formatted payload to send.

    Returns:
        dict: The payload data as a dictionary.

    """
    if not thumbnail or not os.path.isfile(thumbnail):
        thumbnail = images.ImageCache.get_rsc_pixmap(
            'placeholder',
            None,
            common.thumbnail_size,
            get_path=True
        )

    base64_thumbnail = base64.b64encode(open(thumbnail, 'rb').read()).decode()
    data = json.dumps(card)
    data = data.\
        replace('<IMAGE>', base64_thumbnail).\
        replace('<TYPE>', publish_type).\
        replace('<SEQ>', seq).\
        replace('<SHOT>', shot).\
        replace('<PATH>', path).\
        replace('<USER>', user).\
        replace('<DATE>', date)
    return json.loads(data)

