import logging
from rasa_core.interpreter import (
    RegexInterpreter,
    INTENT_MESSAGE_PREFIX)

from rasa_addons.multilingual_interpreter import RasaMultiNLUHttpInterpreter

logger = logging.getLogger(__name__)


def _parse_message(self, message):
    # for testing - you can short-cut the NLU part with a message
    # in the format _intent[entity1=val1,entity=val2]
    # parse_data is a dict of intent & entities
    if message.text.startswith(INTENT_MESSAGE_PREFIX):
        parse_data = RegexInterpreter().parse(message.text)
    elif isinstance(self.interpreter, RasaMultiNLUHttpInterpreter):
        language = message.output_channel.language if hasattr(message.output_channel, 'language') else 'en'
        parse_data = self.interpreter.parse(message.text,
                                            message.output_channel.language,
                                            )
    else:
        parse_data = self.interpreter.parse(message.text)

    logger.debug("Received user message '{}' with intent '{}' "
                 "and entities '{}'".format(message.text,
                                            parse_data["intent"],
                                            parse_data["entities"]))
    return parse_data