from rasa_core.utils import AvailableEndpoints, read_endpoint_config


class MoreAvailableEndpoints(AvailableEndpoints):
    """Collection of configured endpoints."""

    @classmethod
    def read_endpoints(cls, endpoint_file):
        nlg = read_endpoint_config(
                endpoint_file, endpoint_type="nlg")
        nlu = read_endpoint_config(
                endpoint_file, endpoint_type="nlu")
        action = read_endpoint_config(
                endpoint_file, endpoint_type="action_endpoint")
        model = read_endpoint_config(
                endpoint_file, endpoint_type="models")
        tracker_store = read_endpoint_config(
                endpoint_file, endpoint_type="tracker_store")
        event_broker = read_endpoint_config(
                endpoint_file, endpoint_type="event_broker")
        rules = read_endpoint_config(
            endpoint_file, endpoint_type="rules")
        credentials = read_endpoint_config(
            endpoint_file, endpoint_type="credentials")
        nlu_models_info = read_endpoint_config(
            endpoint_file, endpoint_type="nlu_models_info")
        return cls(nlg, nlu, action, model, tracker_store, event_broker, rules, credentials, nlu_models_info)

    def __init__(self,
                 nlg=None,
                 nlu=None,
                 action=None,
                 model=None,
                 tracker_store=None,
                 event_broker=None,
                 rules=None,
                 credentials=None,
                 nlu_models_info=None
                 ):
        self.model = model
        self.action = action
        self.nlu = nlu
        self.nlg = nlg
        self.tracker_store = tracker_store
        self.event_broker = event_broker
        self.rules = rules
        self.credentials = credentials
        self.nlu_models_info = nlu_models_info