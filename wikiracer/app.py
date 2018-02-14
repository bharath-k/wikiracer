#!/usr/bin/python3
import argparse
import asyncio

from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.web import Application

from wikiracer import settings
from wikiracer.base import init, stop
from wikiracer.api import PingRequestHandler, InputRequestHandler
from wikiracer.settings import LISTEN_PORT

loop = asyncio.get_event_loop()

application = Application([
    (r'/api/ping/', PingRequestHandler),
    (r'/api/links/', InputRequestHandler),
])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Wikiracer tornado service",
    )
    args = parser.parse_args()

    init()

    # asyncio.ensure_future(process_inputs())
    AsyncIOMainLoop().install()
    application.listen(settings.LISTEN_PORT)
    try:
        loop.run_forever()
    finally:
        loop.close()
        stop()
