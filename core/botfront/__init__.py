from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from rasa_core.utils import EndpointConfig
from rasa_core.dispatcher import Dispatcher, BotMessage
import logging
import copy
import requests
from rasa_core import constants

logger = logging.getLogger(__name__)

INTENT_MESSAGE_PREFIX = "/"
from rasa_addons.multilingual_interpreter import RasaMultiNLUHttpInterpreter


class BotfrontInterpreter(RasaMultiNLUHttpInterpreter):
    def __init__(self, models=None, endpoint=None, project_name='default', default_language='en'):
        # type: (Text, EndpointConfig, Text) -> None

        self.models = models
        self.default_language = default_language
        self.project_name = project_name

        if endpoint:
            self.endpoint = endpoint
        else:
            self.endpoint = EndpointConfig(constants.DEFAULT_SERVER_URL)

    def get_model(self, lang):
        model = self.models.get(lang)
        if not model:
            model = self.models.get(self.default_language)
        return model

    def parse(self, text, lang):
        """Parse a text message.

        Return a default value if the parsing of the text failed."""

        default_return = {"intent": {"name": "", "confidence": 0.0},
                          "entities": [], "text": ""}
        result = self._rasa_http_parse(text, lang)

        return result if result is not None else default_return

    def _rasa_http_parse(self, text, lang):
        """Send a text message to a running rasa NLU http server.

        Return `None` on failure."""

        if not self.endpoint:
            logger.error(
                "Failed to parse text '{}' using rasa NLU over http. "
                "No rasa NLU server specified!".format(text))
            return None

        params = {
            "token": self.endpoint.token,
            "model": self.get_model(lang),
            "project": self.project_name,
            "q": text
        }
        url = "{}/parse".format(self.endpoint.url)
        try:
            result = requests.get(url, params=params)
            if result.status_code == 200:
                return result.json()
            else:
                logger.error(
                    "Failed to parse text '{}' using rasa NLU over http. "
                    "Error: {}".format(text, result.text))
                return None
        except Exception as e:
            logger.error(
                "Failed to parse text '{}' using rasa NLU over http. "
                "Error: {}".format(text, e))
            return None


class BotfrontDispatcher(Dispatcher):

    def utter_response(self, message):
        # type: (Dict[Text, Any]) -> None
        """Send a message to the client."""
        if type(message) is list:
            for m in message:
                self.utter_response(m)
        else:
            if message.get('template_type') in ['list', 'generic']:
                payload = {'template_type': message.get('template_type')}
                if 'top_element_style' in message:
                    payload['top_element_style'] = message.get('top_element_style')
                payload['elements'] = message.get('elements')
                message['elements'] = payload
            elif message.get('template_type') == 'button':
                payload = {'template_type': 'button', 'text': message.get("text"), 'buttons': message.get("buttons")}
                del message['text']
                del message['buttons']
                message['elements'] = payload
            if message.get('template_type') == 'handoff':
                message['elements'] = copy.deepcopy(message)

            data = {"elements": message.get('elements'),
                    "buttons": message.get("buttons"),
                    "attachment": message.get("image")}

            bot_message = BotMessage(text=message.get("text"), data=data)

            self.latest_bot_messages.append(bot_message)
            self.output_channel.send_response(self.sender_id, message)

    def _generate_response(
        self,
        template,  # type: Text
        tracker,  # type: DialogueStateTracker
        silent_fail=False,  # type: bool
        **kwargs  # type: Any
    ):
        # type: (...) -> Dict[Text, Any]
        """"Generate a response."""

        message = self.nlg.generate(template, tracker,
                                    self.output_channel,
                                    **kwargs)

        if message is None and not silent_fail:
            logger.error("Couldn't create message for template '{}'."
                         "".format(template))

        return message