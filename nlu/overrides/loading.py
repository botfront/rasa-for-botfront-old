from rasa_nlu.training_data import loading
from rasa_nlu.training_data.formats import (
    MarkdownReader, WitReader, LuisReader, DialogflowReader)
from rasa_nlu.training_data.formats.dialogflow import (DIALOGFLOW_INTENT,
    DIALOGFLOW_ENTITIES)
from overrides.rasa import RasaReader


def _reader_factory(fformat):
    """Generates the appropriate reader class based on the file format."""
    WIT = "wit"
    LUIS = "luis"
    RASA = "rasa_nlu"
    MARKDOWN = "md"
    DIALOGFLOW_RELEVANT = {DIALOGFLOW_ENTITIES, DIALOGFLOW_INTENT}
    reader = None
    if fformat == LUIS:
        reader = LuisReader()
    elif fformat == WIT:
        reader = WitReader()
    elif fformat in DIALOGFLOW_RELEVANT:
        reader = DialogflowReader()
    elif fformat == RASA:
        reader = RasaReader()
    elif fformat == MARKDOWN:
        reader = MarkdownReader()
    return reader


def override_reader_factory():
    loading._reader_factory = _reader_factory