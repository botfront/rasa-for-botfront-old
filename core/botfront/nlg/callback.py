from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
from typing import Text, Any, Dict, Optional

from rasa_core.constants import DEFAULT_REQUEST_TIMEOUT
from rasa_core.nlg import CallbackNaturalLanguageGenerator
from rasa_core.nlg.callback import nlg_request_format
from rasa_core.trackers import DialogueStateTracker, EventVerbosity
from rasa_core.utils import EndpointConfig

logger = logging.getLogger(__name__)


class BotfrontCallbackNaturalLanguageGenerator(CallbackNaturalLanguageGenerator):
    """Generate bot utterances by using a remote endpoint for the generation.

    The generator will call the endpoint for each message it wants to
    generate. The endpoint needs to respond with a properly formatted
    json. The generator will use this message to create a response for
    the bot."""

    @staticmethod
    def nlg_response_format_spec():
        """Expected response schema for an NLG endpoint.

        Used for validation of the response returned from the NLG endpoint."""
        return [{
            "type": "object",
            "properties": {
                "text": {
                    "type": "string"
                },
                "buttons": {
                    "type": ["array", "null"],
                    "items": {"type": "object"}
                },
                "elements": {
                    "type": ["array", "null"],
                    "items": {"type": "object"}
                },
                "attachment": {
                    "type": ["object", "null"]
                },
                "image": {
                    "type": ["string", "null"]
                }
            },
        }]

    def generate(self, template_name, tracker, output_channel, **kwargs):
        # type: (Text, DialogueStateTracker, Text, Any) -> Dict[Text, Any]
        """Retrieve a named template from the domain using an endpoint."""

        body = nlg_request_format(template_name,
                                  tracker,
                                  output_channel,
                                  **kwargs)

        logger.debug("Requesting NLG for {} from {}."
                     "".format(template_name, self.nlg_endpoint.url))
        response = self.nlg_endpoint.request(method="post",
                                             json=body,
                                             timeout=DEFAULT_REQUEST_TIMEOUT)
        response.raise_for_status()

        content = response.json()
        if self.validate_response(content):
            return content
        else:
            raise Exception("NLG web endpoint returned an invalid response.")

    @staticmethod
    def validate_response(content):
        # type: (Optional[Dict[Text, Any]]) -> bool
        """Validate the NLG response. Raises exception on failure."""

        from jsonschema import validate
        from jsonschema import ValidationError

        try:
            if content is None or content == "":
                # means the endpoint did not want to respond with anything
                return True
            else:
                validate(content, BotfrontCallbackNaturalLanguageGenerator.nlg_response_format_spec())
                return True
        except ValidationError as e:
            e.message += (
                ". Failed to validate NLG response from API, make sure your "
                "response from the NLG endpoint is valid. ")
            raise e
