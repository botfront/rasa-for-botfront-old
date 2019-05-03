from typing import Any
from typing import List
from typing import Optional
from typing import Text
from rasa_nlu.components import Component
from rasa_nlu.training_data import Message
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Metadata


class LanguageSetter(Component):
    name = 'components.botfront.language_setter.LanguageSetter'

    def __init__(self,
                 component_config: Text = None,
                 language: Optional[List[Text]] = None) -> None:
        super(LanguageSetter, self).__init__(component_config)
        self.language = language

    def process(self, message, **kwargs):
        # type: (Message, **Any) -> None

        message.set("language", self.language, add_to_output=True)

    @classmethod
    def create(cls, config: RasaNLUModelConfig) -> 'LanguageSetter':
        return cls(config.for_component(cls.name,
                                        cls.defaults),
                   config.language)

    @classmethod
    def load(cls,
             model_dir: Text = None,
             model_metadata: Metadata = None,
             cached_component: Optional['LanguageSetter'] = None,
             **kwargs: Any
             ) -> 'LanguageSetter':
        component_config = model_metadata.for_component(cls.name)
        return cls(component_config, model_metadata.get("language"))