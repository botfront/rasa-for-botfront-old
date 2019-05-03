from typing import Any, Dict, Text


def normalise_request_json(self, data: Dict[Text, Any]) -> Dict[Text, Any]:
    _data = {"text": data["q"][0] if type(data["q"]) == list else data["q"]}
    if not data.get("project"):
        _data["project"] = "default"
    elif type(data["project"]) == list:
        _data["project"] = data["project"][0]
    else:
        _data["project"] = data["project"]

    if data.get("model"):
        if type(data["model"]) == list:
            _data["model"] = data["model"][0]
        else:
            _data["model"] = data["model"]

    if "time" in data:
        _data['time'] = data["time"]

    for key in data.keys():
        _data[key] = data[key]
    return _data