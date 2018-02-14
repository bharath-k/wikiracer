import json
import logging

from tornado.web import HTTPError
from tornado.web import RequestHandler

from wikiracer.utils import validate_input
from wikiracer.handler import do_work

logger = logging.getLogger(__name__)

class PingRequestHandler(RequestHandler):
    SUPPORTED_METHODS=('GET')

    def get(self):
        self.set_header('Content-Type', 'text/plain')
        self.write('woohoo!')


class ApiRequestHandler(RequestHandler):
    '''
        Base request handler for apis
    '''

    def write_error(self, status_code, **kwargs):
        result = dict(
            code=status_code,
            status='error',
            message=self._reason,
        )
        # tornado automatically converts dictionary to json output
        # and sets Content-Type as application/json
        self.write(result)
        self.finish()

    def write_ok(self, result=None):
        if result is None:
            result = dict(status='ok')
        self.write(result)

class InputRequestHandler(ApiRequestHandler):
    SUPPORTED_METHODS=('POST')

    async def post(self):
        try:
            # parse input
            data = json.loads(self.request.body.decode())
        except ValueError as e:
            logger.warning("Can't parse request: {}".format(e))
            raise HTTPError(400, reason="Can't parse request")

        try:
            await validate_input(data)
        except ValidationError as e:
            logger.warning("Validation error: {}".format(e))
            raise HTTPError(400, reason=str(e))

        # parse input
        source = data['source']
        destination = data['destination']
        
        try:
            result = await do_work(source, destination)
        except Exception as e:
            logger.warning("Validation error: {}".format(e))
            raise
            # raise HTTPError(400, reason=str(e))
        else:
            self.write_ok(result)
