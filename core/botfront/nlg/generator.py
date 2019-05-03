from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import typing
import requests
import logging
from typing import Optional, Union
from collections import Mapping, Iterable
from rasa_core.trackers import EventVerbosity

from rasa_core.nlg import TemplatedNaturalLanguageGenerator, NaturalLanguageGenerator
from rasa_core.utils import EndpointConfig
from utils import get_latest_parse_data_language, get_project_default_language

if typing.TYPE_CHECKING:
    from rasa_core.domain import Domain

logger = logging.getLogger(__name__)


def process_recursively(container, func, template_vars):
    """ Substitute slots in all parts of the template """
    t = container.__class__

    if isinstance(container, int):
        return container
    if isinstance(container, str):
        return func(container, template_vars)
    elif isinstance(container, Mapping):
        return t((x, process_recursively(container[x], func, template_vars)) for x in container)
    elif isinstance(container, Iterable):
        # Add other non-replicable iterables here. 

        return t(process_recursively(x, func, template_vars) for x in container)
    else:
        raise ValueError("I don't know how to handle container type: %s" %
                         type(container))


def format(value, template_vars):
    try:
        return value.format(**template_vars)
    except KeyError:
        return value


class BotfrontNaturalLanguageGenerator(NaturalLanguageGenerator):
    """Generate bot utterances based on a dialogue state."""

    def generate(self, template_name, tracker, output_channel, **kwargs):
        """Generate a response for the requested template.

        There are a lot of different methods to implement this, e.g. the
        generation can be based on templates or be fully ML based by feeding
        the dialogue state into a machine learning NLG model."""
        raise NotImplementedError

    @staticmethod
    def create(
            obj,  # type: Union[NaturalLanguageGenerator, EndpointConfig, None]
            domain  # type: Optional[Domain]
    ):
        # type: (...) -> NaturalLanguageGenerator
        """Factory to create a generator."""

        if isinstance(obj, NaturalLanguageGenerator):
            return obj
        elif isinstance(obj, EndpointConfig):
            from botfront.nlg.callback import BotfrontCallbackNaturalLanguageGenerator
            return BotfrontCallbackNaturalLanguageGenerator(obj)
        else:
            return LegacyBotfrontNLG(obj)


class LegacyBotfrontNLG(TemplatedNaturalLanguageGenerator):

    def __init__(self, bf_url, project_id):
        # type: (Text) -> None

        self.project_id = project_id
        self.bf_url = bf_url
        super(LegacyBotfrontNLG, self).__init__(templates=None)

    def generate(self, response_name, tracker, output_channel, **kwargs):
        """Retrieve a named template from the domain."""

        language = get_latest_parse_data_language(tracker.current_state(EventVerbosity.ALL)['events'])
        if not language and hasattr(output_channel, 'language'):
            language = output_channel.language
        if not language:
            language = get_project_default_language(self.project_id, self.bf_url)
        if not language:
            language = 'en'

        url = "{base_url}/project/{project_id}/response/name/{response_name}/lang/{lang}".format(
            base_url=self.bf_url, project_id=self.project_id, response_name=response_name,
            lang=language)

        try:
            result = requests.get(url)
            if result.status_code == 200:
                if result.json():
                    filled_slots = tracker.current_slot_values()
                    if hasattr(output_channel, 'user'):
                        facebook_user_info = {'user_{}'.format(key): value for key, value in
                                              output_channel.user.items()}
                        filled_slots.update(facebook_user_info)
                    return list(
                        [process_recursively(message, format, self._template_variables(filled_slots, kwargs)) for
                         message in result.json()]
                    )
                else:
                    return result.json().error
            else:
                logger.error(
                    "Failed to get response '{}' from Botfront. "
                    "Error: {}".format(response_name, result.json()))
                return {"text": response_name}

        except Exception as e:
            logger.error(
                "Failed to get response '{}' from Botfront. "
                "Error: {}".format(response_name, e))
            return {"text": response_name}
