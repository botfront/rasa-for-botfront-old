from overrides import monkey_patch
monkey_patch()
from overrides.data_router import BFDataRouter
import logging
import os
import simplejson
from twisted.internet import threads
from twisted.internet.defer import returnValue

from rasa_nlu.utils import read_endpoints
from rasa_nlu import utils
from rasa_nlu.server import create_argument_parser
from rasa_nlu.data_router import (
    InvalidProjectError)
from rasa_nlu.utils import json_to_string

from rasa_nlu.server import RasaNLU, requires_auth, check_cors, inlineCallbacks, decode_parameters
logger = logging.getLogger(__name__)


class BFRasaNLU(RasaNLU):

    @RasaNLU.app.route("/parse", methods=['GET', 'POST', 'OPTIONS'])
    @requires_auth
    @check_cors
    @inlineCallbacks
    def parse(self, request):
        request.setHeader('Content-Type', 'application/json')
        if request.method.decode('utf-8', 'strict') == 'GET':
            request_params = decode_parameters(request)
        else:
            request_params = simplejson.loads(
                request.content.read().decode('utf-8', 'strict'))

        if 'query' in request_params:
            request_params['q'] = request_params.pop('query')

        if 'q' not in request_params:
            request.setResponseCode(404)
            dumped = json_to_string(
                {"error": "Invalid parse parameter specified"})
            returnValue(dumped)
        else:
            data = self.data_router.extract(request_params)
            try:
                request.setResponseCode(200)
                response = yield (self.data_router.parse(data, request_params) if self._testing
                                  else threads.deferToThread(
                    self.data_router.parse, data, request_params))
                returnValue(json_to_string(response))
            except InvalidProjectError as e:
                request.setResponseCode(404)
                returnValue(json_to_string({"error": "{}".format(e)}))
            except Exception as e:
                request.setResponseCode(500)
                logger.exception(e)
                returnValue(json_to_string({"error": "{}".format(e)}))


logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Running as standalone python application
    cmdline_args = create_argument_parser().parse_args()

    utils.configure_colored_logging(cmdline_args.loglevel)
    pre_load = cmdline_args.pre_load

    _endpoints = read_endpoints(cmdline_args.endpoints)

    router = BFDataRouter(
            cmdline_args.path,
            cmdline_args.max_training_processes,
            cmdline_args.response_log,
            cmdline_args.emulate,
            cmdline_args.storage,
            model_server=_endpoints.model,
            wait_time_between_pulls=cmdline_args.wait_time_between_pulls
    )

    if pre_load:
        logger.debug('Preloading....')
        if 'all' in pre_load:
            pre_load = router.project_store.keys()
        router._pre_load(pre_load)

    rasa = BFRasaNLU(
            router,
            cmdline_args.loglevel,
            cmdline_args.write,
            cmdline_args.num_threads,
            os.environ.get('AUTH_TOKEN', None),
            cmdline_args.cors,
            default_config_path=cmdline_args.config
    )

    logger.info('Started http server on port %s' % cmdline_args.port)
    rasa.app.run('0.0.0.0', cmdline_args.port)