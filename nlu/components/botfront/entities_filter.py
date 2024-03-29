from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os

import requests
import simplejson
from rasa_nlu.components import Component
from typing import Any
from typing import List
from typing import Optional
from typing import Text

from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Metadata
from rasa_nlu.training_data import Message

logger = logging.getLogger(__name__)


class EntitiesFilter(Component):
    """Filter entities wrt intent"""

    name = "components.botfront.entities_filter.EntitiesFilter"
    provides = ["entities"]
    defaults = {
        "entities": {}
    }

    def __init__(self, component_config=None):
        # type: (Text, Optional[List[Text]]) -> None

        super(EntitiesFilter, self).__init__(component_config)

    @classmethod
    def create(cls, config):
        # type: (RasaNLUModelConfig) -> DucklingCrfMerger

        return EntitiesFilter(config.for_component(cls.name,  cls.defaults))

    def process(self, message, **kwargs):
        # type: (Message, **Any) -> None

        # get intent
        intent = message.get("intent")
        if intent is None:
            logger.warn("No intent found")

        # get crf and duckling entities
        message_entities = message.get("entities")
        entities_to_filter = filter(lambda e: e["extractor"] in ["ner_crf", "ner_duckling_http"], message_entities)
        indices_to_remove = []
        for index, entity in enumerate(entities_to_filter):
            if intent["name"] in self.component_config["entities"].keys() and entity["entity"] not in self.component_config["entities"][intent["name"]]:
                indices_to_remove.append(index)

        for i in sorted(indices_to_remove, reverse=True):
            del message.get("entities")[i]

    @classmethod
    def load(cls,
             model_dir=None,  # type: Text
             model_metadata=None,  # type: Metadata
             cached_component=None,  # type: Optional[EntitiesFilter]
             **kwargs  # type: **Any
             ):
        # type: (...) -> EntitiesFilter

        component_config = model_metadata.for_component(cls.name)
        return cls(component_config)
