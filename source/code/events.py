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
    events = ['bodySizeDidChange', 'bitSizeDidChange', 'simulationVisibilityDidChange',
              'errorsVisibilityDidChange', 'previewDidChange']

    for methodName in events:
        eventName = f"{DEFAULT_KEY}.{methodName}"
        if eventName not in getRegisteredSubscriberEvents():
            registerSubscriberEvent(
                subscriberEventName=eventName,
                methodName=methodName,
                lowLevelEventNames=[eventName],
                dispatcher="roboFont",
                delay=0,
                debug=DEBUG_MODE
            )
