import enum

from .. import common


class State(enum.IntEnum):
    Omitted = common.idx(reset=True, start=0)
    OnHold = common.idx()
    NotStarted = common.idx()
    InProgress = common.idx()
    PendingReview = common.idx()
    Priority = common.idx()
    Approved = common.idx()
    Completed = common.idx()


STATES = {
    State.NotStarted: {
        'icon': 'state_not_started',
        'description': 'The task has not been started yet',
        'color': common.Color.SecondaryText()
    },
    State.InProgress: {
        'icon': 'state_in_progress',
        'description': 'The task is currently being worked on',
        'color': common.Color.Blue()
    },
    State.PendingReview: {
        'icon': 'state_pending_review',
        'description': 'The task is completed and awaiting review',
        'color': common.Color.Yellow()
    },
    State.Priority: {
        'icon': 'state_priority',
        'description': 'The task has been marked as high priority',
        'color': common.Color.Red()
    },
    State.Approved: {
        'icon': 'state_approved',
        'description': 'The task has been reviewed and approved',
        'color': common.Color.Green()
    },
    State.Completed: {
        'icon': 'state_completed',
        'description': 'The task is finished and no further action is required',
        'color': common.Color.Green()
    },
    State.OnHold: {
        'icon': 'state_on_hold',
        'description': 'The task is temporarily paused',
        'color': common.Color.Yellow()
    },
    State.Omitted: {
        'icon': 'state_omitted',
        'description': 'The task is skipped or not required',
        'color': common.Color.VeryDarkBackground()
    },
}
