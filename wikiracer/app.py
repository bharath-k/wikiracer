#!/usr/bin/python3
import argparse
import asyncio

from aiohttp import web

from wikiracer import settings
from wikiracer.base import init, stop
from wikiracer.api import ping_handler, links_handler
from wikiracer.settings import LISTEN_PORT

loop = asyncio.get_event_loop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Wikiracer web service",
    )
    args = parser.parse_args()
    # TODO: fetch log mode or additional details using args.
    init()
    loop = asyncio.get_event_loop()
    app = web.Application(loop=loop)
    # add routes
    app.router.add_get('/api/ping', ping_handler)
    app.router.add_post('/api/links', links_handler)
    try:
        web.run_app(app,host='0.0.0.0',port=LISTEN_PORT)
    finally:
        loop.close()
        stop()
