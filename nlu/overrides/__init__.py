import rasa_nlu.evaluate
from rasa_nlu.model import Interpreter
from rasa_nlu.project import Project
from overrides.loading import override_reader_factory
from rasa_nlu.emulators import NoEmulator
from overrides import model as model_override
from overrides import project as project_override
from overrides.emulators__init__ import normalise_request_json
from overrides.evaluate import run_evaluation, evaluate_intents, get_intent_predictions, IntentEvaluationResult


def monkey_patch():
    override_reader_factory()
    Interpreter.parse = model_override.parse
    Project.parse = project_override.parse
    NoEmulator.normalise_request_json = normalise_request_json
    rasa_nlu.evaluate.evaluate_intents = evaluate_intents
    rasa_nlu.evaluate.get_intent_predictions = get_intent_predictions
    rasa_nlu.evaluate.run_evaluation = run_evaluation

