"""Task progress tracker for asset items.

This module provides the basic definitions needed to implement task status tracking.
The progress data is stored in the asset table under the 'progress' column.

:attr:`STATES` defines the user selectable progress states.
:attr:`STAGES` define the production steps we're able to set states for. Each asset item
has their own STAGES data stored in the bookmark database, editable by user interactions
via the :class:`ProgressDelegate`.

"""

from . import common

n = (f for f in range(9999))
DesignStage = next(n)
LayoutStage = next(n)
ModelStage = next(n)
RigStage = next(n)
AnimationStage = next(n)
RenderStage = next(n)
FXStage = next(n)
CompStage = next(n)
GradeStage = next(n)

n = (f for f in range(9999))
OmittedState = next(n)
InProgressState = next(n)
PendingState = next(n)
CompletedState = next(n)
PriorityState = next(n)

#: The selectable progress states
STATES = {
    OmittedState: {
        'name': 'Skip',
        'icon': 'progress-dot-24',
        'color': common.Color.Opaque(),
    },
    InProgressState: {
        'name': 'In\nProgress',
        'icon': 'progress-hourglass-24',
        'color': common.Color.Yellow(),
    },
    PendingState: {
        'name': 'Pending',
        'icon': 'progress-task-planning-24',
        'color': common.Color.Background(),
    },
    CompletedState: {
        'name': 'Done',
        'icon': 'progress-task-completed-24',
        'color': common.Color.Green(),
    },
    PriorityState: {
        'name': 'Priority',
        'icon': 'progress-task-important-24',
        'color': common.Color.DarkRed(),
    },
}

#: The production stages to be configured with a :attr:`STATES` value.
STAGES = {
    ModelStage: {
        'name': 'Model',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    RigStage: {
        'name': 'Rig',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    DesignStage: {
        'name': 'Design',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    LayoutStage: {
        'name': 'Layout',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    AnimationStage: {
        'name': 'Anim',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    RenderStage: {
        'name': 'Render',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    FXStage: {
        'name': 'FX',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    CompStage: {
        'name': 'Comp',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    GradeStage: {
        'name': 'Grade',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
}
