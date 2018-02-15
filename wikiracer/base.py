import asyncio
import functools
import logging
import signal

from wikiracer import settings

loop = asyncio.get_event_loop()

def signal_handler(signame):
    print("Got signal {}, terminating...".format(signame))
    loop.stop()


def init():
    # Add signal handlers
    for signame in ('SIGTERM', 'SIGINT'):
        loop.add_signal_handler(
            getattr(signal, signame),
            functools.partial(signal_handler, signame),
        )

    # Configure logger
    logger_defaults = {
        'level': logging.DEBUG,
        'format': '%(asctime)s|%(name)s|%(levelname)s|%(message)s',
    }
    logging.basicConfig(**logger_defaults)

def stop():
    pass
