from rasa_nlu.training_data import Message


def parse(self, text, time=None, only_output_properties=True, request_params=None):
    # type: (Text) -> Dict[Text, Any]
    """Parse the input text, classify it and return pipeline result.

    The pipeline result usually contains intent and entities."""

    if not text:
        # Not all components are able to handle empty strings. So we need
        # to prevent that... This default return will not contain all
        # output attributes of all components, but in the end, no one
        # should pass an empty string in the first place.
        output = self.default_output_attributes()
        output["text"] = ""
        return output

    message = Message(text, self.default_output_attributes(), time=time)

    for component in self.pipeline:
        component.process(message, **self.context, request_params=request_params)

    output = self.default_output_attributes()
    output.update(message.as_dict(
        only_output_properties=only_output_properties))
    return output
