import os
import yaml
import logging
import tempfile
import requests
from rasa_core.events import UserUttered, BotUttered, SlotSet
from requests.exceptions import RequestException
logger = logging.getLogger(__name__)


def load_from_remote(endpoint, type, temp_file=True):
    try:
        response = endpoint.request(method='get')
        logger.debug("Requesting {} from server {}..."
                     "".format(type, endpoint.url))
        if response.status_code in [204, 304]:
            logger.debug("Model server returned {} status code, indicating "
                         "that no new {} are available.".format(response.status_code, type))
            return None
        elif response.status_code == 404:
            logger.warning("Tried to fetch {} from server but got a 404 response".format(type))
            return None
        elif response.status_code != 200:
            logger.warning("Tried to fetch {} from server, but server response "
                           "status code is {}."
                           "".format(type, response.status_code))
        else:
            if temp_file is True:
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as yamlfile:
                    yaml.dump(response.json(), yamlfile)
                return yamlfile.name
            else:
                return response.json()

    except RequestException as e:
        logger.warning("Tried to fetch rules from server, but couldn't reach "
                       "server. We'll retry later... Error: {}."
                       "".format(e))


def get_latest_parse_data_language(all_events):
    events = reversed(all_events)
    try:
        while True:
            event = next(events)
            if event['event'] == 'user' and 'parse_data' in event and 'language' in event['parse_data']:
                return event['parse_data']['language']

    except StopIteration:
        return None


def get_project_default_language(project_id, base_url):
    url = '{base_url}/project/{project_id}/models/published'.format(base_url=base_url, project_id=project_id)
    result = requests.get(url);
    try:
        result = requests.get(url)
        if result.status_code == 200:
            if result.json():
                return result.json().get('default_language', None)
            else:
                return result.json().error
        else:
            logger.error(
                "Failed to get project default language"
                "Error: {}".format(result.json()))
            return None

    except Exception as e:
        logger.error(
            "Failed to get project default language"
            "Error: {}".format(result.json()))
        return None


def events_to_dialogue(events):
    dialogue = ""
    for e in events:
        if e["event"] == 'user':
            dialogue += "\n User: {}".format(e['text'])
        elif e["event"] == 'bot':
            dialogue += "\n Bot: {}".format(e['text'])
    return dialogue


def slots_from_profile(user_id, user_profile):
    return [SlotSet("user_id", user_id), SlotSet("first_name", user_profile["first_name"]),
            SlotSet("last_name", user_profile["last_name"]), SlotSet("phone", user_profile["phone"]),
            SlotSet('user_profile', user_profile)]
