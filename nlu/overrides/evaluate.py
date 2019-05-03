import os
import logging
from rasa_nlu import training_data, utils
from rasa_nlu.model import Interpreter
from collections import namedtuple
from rasa_nlu.evaluate import extract_intent, extract_message, extract_confidence, extract_entities, \
    plot_intent_confidences, plot_confusion_matrix, collect_nlu_errors, collect_nlu_successes, log_evaluation_table, \
    get_evaluation_metrics, remove_empty_intent_examples, _targets_predictions_from, save_json, get_entity_extractors, \
    remove_duckling_entities, remove_duckling_extractors, get_entity_predictions, is_intent_classifier_present, \
    get_entity_targets, evaluate_entities, get_intent_targets

logger = logging.getLogger(__name__)

duckling_extractors = {"ner_duckling_http", "components.botfront.duckling_http_extractor.DucklingHTTPExtractor"}

IntentEvaluationResult = namedtuple('IntentEvaluationResult',
                                    'target '
                                    'target_entities '
                                    'prediction '
                                    'message '
                                    'confidence '
                                    'entities_prediction ')


def run_evaluation(data_path, model,
                   report_folder=None,
                   successes_filename=None,
                   errors_filename='errors.json',
                   confmat_filename=None,
                   intent_hist_filename=None,
                   component_builder=None):  # pragma: no cover
    """Evaluate intent classification and entity extraction."""

    # get the metadata config from the package data
    if isinstance(model, Interpreter):
        interpreter = model
    else:
        interpreter = Interpreter.load(model, component_builder)
    test_data = training_data.load_data(data_path,
                                        interpreter.model_metadata.language)
    extractors = get_entity_extractors(interpreter)
    entity_predictions, tokens = get_entity_predictions(interpreter,
                                                        test_data)

    if duckling_extractors.intersection(extractors):
        entity_predictions = remove_duckling_entities(entity_predictions)
        extractors = remove_duckling_extractors(extractors)

    result = {
        "intent_evaluation": None,
        "entity_evaluation": None
    }

    if report_folder:
        utils.create_dir(report_folder)

    if is_intent_classifier_present(interpreter):
        intent_targets = get_intent_targets(test_data)
        intent_results = get_intent_predictions(
                intent_targets, interpreter, test_data)

        logger.info("Intent evaluation results:")
        result['intent_evaluation'] = evaluate_intents(intent_results,
                                                       report_folder,
                                                       successes_filename,
                                                       errors_filename,
                                                       confmat_filename,
                                                       intent_hist_filename)

    if extractors:
        entity_targets = get_entity_targets(test_data)

        logger.info("Entity evaluation results:")
        result['entity_evaluation'] = evaluate_entities(entity_targets,
                                                        entity_predictions,
                                                        tokens,
                                                        extractors,
                                                        report_folder)

    return result


def evaluate_intents(intent_results,
                     report_folder,
                     successes_filename,
                     errors_filename,
                     confmat_filename,
                     intent_hist_filename):  # pragma: no cover
    """Creates a confusion matrix and summary statistics for intent predictions.
    Log samples which could not be classified correctly and save them to file.
    Creates a confidence histogram which is saved to file.
    Wrong and correct prediction confidences will be
    plotted in separate bars of the same histogram plot.
    Only considers those examples with a set intent.
    Others are filtered out. Returns a dictionary of containing the
    evaluation result."""

    # remove empty intent targets
    num_examples = len(intent_results)
    intent_results = remove_empty_intent_examples(intent_results)

    logger.info("Intent Evaluation: Only considering those "
                "{} examples that have a defined intent out "
                "of {} examples".format(len(intent_results), num_examples))

    targets, predictions = _targets_predictions_from(intent_results)

    if report_folder:
        report, precision, f1, accuracy = get_evaluation_metrics(
                targets, predictions, output_dict=True)

        report_filename = os.path.join(report_folder, 'intent_report.json')

        save_json(report, report_filename)
        logger.info("Classification report saved to {}."
                    .format(report_filename))

    else:
        report, precision, f1, accuracy = get_evaluation_metrics(targets,
                                                                 predictions)
        log_evaluation_table(report, precision, f1, accuracy)

    if successes_filename:
        # save classified samples to file for debugging
        collect_nlu_successes(intent_results, successes_filename)

    if errors_filename:
        # log and save misclassified samples to file for debugging
        collect_nlu_errors(intent_results, errors_filename)

    if confmat_filename:
        from sklearn.metrics import confusion_matrix
        from sklearn.utils.multiclass import unique_labels
        import matplotlib.pyplot as plt

        cnf_matrix = confusion_matrix(targets, predictions)
        labels = unique_labels(targets, predictions)
        plot_confusion_matrix(cnf_matrix, classes=labels,
                              title='Intent Confusion matrix',
                              out=confmat_filename)
        plt.show()

        plot_intent_confidences(intent_results,
                                intent_hist_filename)

        plt.show()

    predictions = [
        {
            "text": res.message,
            "intent": res.target,
            "entities": res.target_entities,
            "predicted_entities": res.entities_prediction,
            "predicted": res.prediction,
            "confidence": res.confidence
        } for res in intent_results
    ]

    return {
        "predictions": predictions,
        "report": report,
        "precision": precision,
        "f1_score": f1,
        "accuracy": accuracy
    }


def get_intent_predictions(targets, interpreter,
                           test_data):  # pragma: no cover
    """Runs the model for the test set and extracts intent predictions.
        Returns intent predictions, the original messages
        and the confidences of the predictions"""
    intent_results = []
    for e, target in zip(test_data.training_examples, targets):
        res = interpreter.parse(e.text, only_output_properties=False)
        intent_results.append(IntentEvaluationResult(
                target,
                e.data.get('entities', []),
                extract_intent(res),
                extract_message(res),
                extract_confidence(res),
                extract_entities(res))
        )

    return intent_results