from gevent import monkey
monkey.patch_all()

import logging
import os

import utils as bf_utils
from botfront.agent import BotfrontAgent
from overrides.utils import MoreAvailableEndpoints
from rasa_core import run
from rasa_core import utils
from rasa_core.broker import PikaProducer
from rasa_core.tracker_store import TrackerStore
from rasa_core.utils import EndpointConfig
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

# Monkey patching dispatcher
import rasa_core.dispatcher
from botfront import BotfrontDispatcher
rasa_core.dispatcher.Dispatcher = BotfrontDispatcher
# Monkey patching processor
from overrides.processor import _parse_message
from rasa_addons.superagent import SuperMessageProcessor
SuperMessageProcessor._parse_message = _parse_message




def load_agent(core_model, nlu_models, project_id, endpoints, tracker_store=None, rules=None):
    bf_api_endpoint = os.environ.get('BF_URL', 'http://localhost:3000')
    wait_time_between_pulls = int(os.environ.get('WAIT_TIME_BETWEEN_PULLS', 60))
    rules = rules if rules is not None else endpoints.rules
    nlu_models = nlu_models if nlu_models is not None else endpoints.nlu_models_info
    return BotfrontAgent.load(path=core_model,
                              project_id=project_id,
                              nlu_models=nlu_models,
                              base_url=bf_api_endpoint,
                              tracker_store=tracker_store,
                              nlu_endpoint=endpoints.nlu,
                              action_endpoint=endpoints.action,
                              model_server=endpoints.model,
                              wait_time_between_pulls=wait_time_between_pulls,
                              rules=rules,
                              )


if __name__ == '__main__':
    arg_parser = run.create_argument_parser()
    arg_parser.add_argument(
        '-r', '--rules',
        required=False,
        type=str,
        help="rules file")
    cmdline_args = arg_parser.parse_args()
    project_id = os.environ.get('BF_PROJECT_ID')
    bf_url = os.environ.get('BF_URL')
    if not project_id:
        raise ValueError('The BF_PROJECT_ID environment variable must be set')
    if not bf_url:
        raise ValueError('The BF_URL environment variable must be set')

    logging.getLogger('werkzeug').setLevel(logging.WARN)
    logging.getLogger('matplotlib').setLevel(logging.WARN)

    utils.configure_colored_logging(cmdline_args.loglevel)
    utils.configure_file_logging(cmdline_args.loglevel,
                                 cmdline_args.log_file)

    logger.info("Rasa process starting")

    # Try fetching from remote if no endpoints or credentials files are provided

    if not cmdline_args.endpoints:
        logger.info("Fetching endpoints from server")
        url = "{}/project/{}/{}".format(bf_url, project_id, "endpoints")
        try:
            cmdline_args.endpoints = bf_utils.load_from_remote(EndpointConfig(url=url), "endpoints")
        except Exception as e:
            print (e)
            raise ValueError('No endpoints found for project {}.'.format(project_id))

    if not cmdline_args.credentials:
        logger.info("Fetching credentials from server")
        url = "{}/project/{}/{}".format(bf_url, project_id, "credentials")
        try:
            cmdline_args.credentials = bf_utils.load_from_remote(EndpointConfig(url=url), "credentials")
        except Exception as e:
            print (e)
            raise ValueError('No credentials found for project {}.'.format(project_id))

    _endpoints = MoreAvailableEndpoints.read_endpoints(cmdline_args.endpoints)

    _broker = PikaProducer.from_endpoint_config(_endpoints.event_broker)

    _tracker_store = TrackerStore.find_tracker_store(
        None, _endpoints.tracker_store, _broker)
    _agent = load_agent(cmdline_args.core,
                        nlu_models=None,
                        project_id=_endpoints.nlu.kwargs.get('project'),
                        tracker_store=_tracker_store,
                        endpoints=_endpoints,
                        rules=cmdline_args.rules)

    run.serve_application(_agent,
                          cmdline_args.connector,
                          cmdline_args.port,
                          cmdline_args.credentials,
                          cmdline_args.cors,
                          os.environ.get('AUTH_TOKEN', None),
                          cmdline_args.enable_api,
                          cmdline_args.jwt_secret,
                          cmdline_args.jwt_method)
