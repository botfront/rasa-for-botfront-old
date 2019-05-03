def parse(self, text, time=None, requested_model_name=None, request_params=None):
    self._begin_read()

    model_name = self._dynamic_load_model(requested_model_name)

    self._loader_lock.acquire()
    try:
        if not self._models.get(model_name):
            interpreter = self._interpreter_for_model(model_name)
            self._models[model_name] = interpreter
    finally:
        self._loader_lock.release()

    response = self._models[model_name].parse(text, time, request_params=request_params)
    response['project'] = self._project
    response['model'] = model_name

    self._end_read()

    return response