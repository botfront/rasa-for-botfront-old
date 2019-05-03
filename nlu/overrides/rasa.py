from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
from collections import defaultdict

from rasa_nlu.training_data import Message
from rasa_nlu.training_data.formats.readerwriter import (
    JsonTrainingDataReader,
    TrainingDataWriter)
from rasa_nlu.training_data.util import transform_entity_synonyms
from rasa_nlu.utils import json_to_string

from overrides.training_data import TrainingData
from rasa_nlu.training_data.formats.rasa import validate_rasa_nlu_data
logger = logging.getLogger(__name__)


class RasaReader(JsonTrainingDataReader):
    def read_from_json(self, js, **kwargs):
        """Loads training data stored in the rasa NLU data format."""
        validate_rasa_nlu_data(js)

        data = js['rasa_nlu_data']
        common_examples = data.get("common_examples", [])
        intent_examples = data.get("intent_examples", [])
        entity_examples = data.get("entity_examples", [])
        entity_synonyms = data.get("entity_synonyms", [])
        regex_features = data.get("regex_features", [])
        fuzzy_gazette = data.get("fuzzy_gazette", [])
        lookup_tables = data.get("lookup_tables", [])

        entity_synonyms = transform_entity_synonyms(entity_synonyms)

        if intent_examples or entity_examples:
            logger.warn("DEPRECATION warning: your rasa data "
                        "contains 'intent_examples' "
                        "or 'entity_examples' which will be "
                        "removed in the future. Consider "
                        "putting all your examples "
                        "into the 'common_examples' section.")

        all_examples = common_examples + intent_examples + entity_examples
        training_examples = []
        for ex in all_examples:
            msg = Message.build(ex['text'], ex.get("intent"),
                                ex.get("entities"))
            training_examples.append(msg)

        return TrainingData(training_examples, entity_synonyms,
                            regex_features, fuzzy_gazette, lookup_tables)


class RasaWriter(TrainingDataWriter):
    def dumps(self, training_data, **kwargs):
        """Writes Training Data to a string in json format."""
        js_entity_synonyms = defaultdict(list)
        for k, v in training_data.entity_synonyms.items():
            if k != v:
                js_entity_synonyms[v].append(k)

        formatted_synonyms = [{'value': value, 'synonyms': syns}
                              for value, syns in js_entity_synonyms.items()]

        formatted_examples = [example.as_dict()
                              for example in training_data.training_examples]

        return json_to_string({
            "rasa_nlu_data": {
                "common_examples": formatted_examples,
                "regex_features": training_data.regex_features,
                "entity_synonyms": formatted_synonyms,
                "fuzzy_gazette": training_data.fuzzy_gazette,
                "lookup_tables": training_data.lookup_tables,
            }
        }, **kwargs)