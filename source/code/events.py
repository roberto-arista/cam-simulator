#!/usr/bin/env python3

# ------ #
# Events #
# ------ #

# -- Modules -- #
from mojo.subscriber import registerSubscriberEvent, getRegisteredSubscriberEvents


# -- Constants -- #
DEBUG_MODE = True
DEFAULT_KEY = 'it.robertoArista.CAMSimulator'


# -- Instructions -- #
if __name__ == '__main__':
    events = [
        ('bodySizeDidChange', 0.25),
        ('bitSizeDidChange', 0.25),
        ('simulationVisibilityDidChange', 0),
        ('errorsVisibilityDidChange', 0),
        ('previewDidChange', 0.25),
    ]

    for methodName, delay in events:
        eventName = f"{DEFAULT_KEY}.{methodName}"
        if eventName not in getRegisteredSubscriberEvents():
            registerSubscriberEvent(
                subscriberEventName=eventName,
                methodName=methodName,
                lowLevelEventNames=[eventName],
                dispatcher="roboFont",
                delay=delay,
                debug=DEBUG_MODE
            )
