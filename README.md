## Versions
* Rasa NLU: 0.14.4
* Rasa Core: 0.13.5
* Rasa SDK: 0.12.1

## Rasa NLU

A slightly modified version of Rasa NLU to be used with Botfront.
This is not a fork, but a standalone python app with Rasa NLU as a dependency. 
This makes sticking to an official Rasa NLU version easier.
Botfront functionalities are added by:
- subclassing or monkey patching for core functionalites (`overrides` folder)
- creating new pipeline components (`components` folder)
 

#### Passing `parse` query string arguments along the Rasa NLU pipeline
Those changes allow to pass query string arguments along the pipeline. It is currently used in 2 features:
- Parse requests without logging them (a `nolog=1` param is passed)
- Pass user timezone and reference time to the Ducking component

The table below lists the modifications

| Rasa NLU Location                                                                                      | BF location                    | Description                       |
| ------------------------------------------------------------------------------------------------------ |:-------------------------------| :-------------------------------- |
| [rasa_nlu/data_router.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/data_router.py)      | `BFDataRouter.parse`           | `parse` method overriden          |
| [rasa_nlu/model.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/model.py)                  | `model.Interpreter.parse`      | `parse` method overriden          |
| [rasa_nlu/project.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/project.py)              | `project.parse`                | `parse` method overriden          |
| [rasa_nlu/server.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/server.py)                | `BFRasaNLU.parse`              | `parse` method/route overriden    |
| [rasa_nlu/emulators/__init__.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/emulators/__init__.py) | `normalise_request_json` | Do not remove query string params    |


 
#### Fuzzy gazette

| Rasa NLU Location                                                                                                                  | BF location                            | Description                 |
| ---------------------------------------------------------------------------------------------------------------------------------- |:---------------------------------------| :-------------------------- |
| [rasa_nlu/training_data/formats/rasa.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/training_data/formats/rasa.py)    | `rasa.RasaWriter.dumps`                | fuzzy_gazette support       |
|                                                                                                                                    | `RasaReader.read_from_json`            | fuzzy_gazette support       |
| [rasa_nlu/training_data/training_data.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/training_data/training_data.py)  | `training_data.TrainingData.__init__`  | fuzzy_gazette support       |
|                                                                                                                                    | `training_data.TrainingData.merge`     | fuzzy_gazette support       |   
| [rasa_nlu/training_data/loading.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/training_data/loading.py)              | `loading.override_reader_factory`      | fuzzy_gazette support       |


#### Evaluation of entities

Botfront displays reports showing entity error on a per example basis. The following modifications are necessary.

| Rasa NLU Location                                                                                                                  | BF location                            | Description                 |
| ---------------------------------------------------------------------------------------------------------------------------------- |:---------------------------------------| :-------------------------- |
| [rasa_nlu/training_data/rasa_nlu/evaluate.py](https://github.com/RasaHQ/rasa_nlu/blob/0.14.4/rasa_nlu/evaluate.py)                 | `get_intent_predictions`               | Add entities to predictions |
|                                                                                                                                    | `evaluate_intents`                     | Add entities to predictions |
|                                                                                                                                    | `IntentEvaluationResult`               | Add entities to predictions |

## Rasa Core

Following the same approach as Rasa NLU, Rasa Core is monkey patched or augmented to support Botfront functionalites

### Multilingualism

Monkey patch

| Rasa Core Location                                                                                                                  | BF location                            | Description                   |
| ----------------------------------------------------------------------------------------------------------------------------------  |:---------------------------------------| :--------------------------   |
| [rasa_nlu/training_data/rasa_core/utils.py](https://github.com/RasaHQ/rasa_core/blob/0.13.5/rasa_core/utils.py)                     | `read_endpoints`                       | Add models infos to endpoints |

Augmentations:

- `core/bot` contains adapted facebook and webchat channels
- `core/botfront` contains adapted nlg classes/function to support sequences and multilingualism
- `core/tracker_stores` contains the Botfront tracker store and analytics platform classes
- `core` contains customized Agent, Interpreter.

This Rasa Core version also uses the [Rasa Addons](https://github.com/mrbot-ai/rasa-addons) package

## Buiding images locally
From the root of the project, run:
```bash
docker build -f Dockerfile_nlu -t gcr.io/botfront-project/simple-nlu:latest .
docker build -f Dockerfile_core -t gcr.io/botfront-project/simple-core:latest .
```
Or run the `build_images.sh` script to build all images at once