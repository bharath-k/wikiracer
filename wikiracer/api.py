import json
import logging

from aiohttp import web

from wikiracer.utils import validate_input, ValidationError
from wikiracer.handler import do_work

logger = logging.getLogger(__name__)


async def ping_handler(request):
    '''
    '''
    # TODO: Set header and write woohoo.
    return web.Response(text='woohoo')


async def links_handler(request):
    '''
    Handle links request.
    '''
    # parse input
    try:
        data= await request.json()
    except ValueError as e:
        logger.warning("Can't parse request: {}".format(e))
        raise web.HTTPBadRequest(text=str(e))
    # validate input
    try:
        await validate_input(data)
    except ValidationError as e:
        logger.warning("Validation error: {}".format(e))
        raise
        # raise web.HTTPBadRequest(text=str(e))
    source = data['source']
    destination = data['destination']
    try:
        result = await do_work(source, destination)
    except Exception as e:
        logger.warning("Validation error: {}".format(e))
        raise
        # raise web.HTTPNotFound(text=str(e))
    else:
        return web.json_response(result)

