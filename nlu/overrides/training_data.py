# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from copy import deepcopy
from rasa_nlu.training_data import Message, TrainingData
from typing import Dict
from typing import List
from typing import Optional
from typing import Text

from rasa_nlu.training_data.util import check_duplicate_synonym

logger = logging.getLogger(__name__)


class TrainingData(TrainingData):
    """Holds loaded intent and entity training data."""

    # Validation will ensure and warn if these lower limits are not met
    MIN_EXAMPLES_PER_INTENT = 2
    MIN_EXAMPLES_PER_ENTITY = 2

    def __init__(self,
                 training_examples=None,
                 entity_synonyms=None,
                 regex_features=None,
                 fuzzy_gazette=None,
                 lookup_tables=None):
        # type: (Optional[List[Message]], Optional[Dict[Text, Text]]) -> None

        if training_examples:
            self.training_examples = self.sanitize_examples(training_examples)
        else:
            self.training_examples = []
        self.entity_synonyms = entity_synonyms if entity_synonyms else {}
        self.regex_features = regex_features if regex_features else []
        self.fuzzy_gazette = fuzzy_gazette if fuzzy_gazette else []
        self.sort_regex_features()
        self.lookup_tables = lookup_tables if lookup_tables else []

        self.print_stats()

    def merge(self, *others):
        """Return merged instance of this data with other training data."""

        training_examples = deepcopy(self.training_examples)
        entity_synonyms = self.entity_synonyms.copy()
        regex_features = deepcopy(self.regex_features)
        fuzzy_gazette = deepcopy(self.fuzzy_gazette)
        lookup_tables = deepcopy(self.lookup_tables)

        for o in others:
            training_examples.extend(deepcopy(o.training_examples))
            regex_features.extend(deepcopy(o.regex_features))
            lookup_tables.extend(deepcopy(o.lookup_tables))

            for text, syn in o.entity_synonyms.items():
                check_duplicate_synonym(entity_synonyms, text, syn,
                                        "merging training data")

            entity_synonyms.update(o.entity_synonyms)

        return TrainingData(training_examples, entity_synonyms,
                            regex_features, fuzzy_gazette, lookup_tables)


