
from rasa_nlu.data_router import DataRouter
from rasa_nlu.project import Project
from rasa_nlu.model import InvalidProjectError
from rasa_nlu.config import RasaNLUModelConfig
import logging
logger = logging.getLogger(__name__)


class BFDataRouter(DataRouter):

    def parse(self, data, request_params=None):
        project = data.get("project", RasaNLUModelConfig.DEFAULT_PROJECT_NAME)
        model = data.get("model")

        if project not in self.project_store:
            projects = self._list_projects(self.project_dir)

            cloud_provided_projects = self._list_projects_in_cloud()
            projects.extend(cloud_provided_projects)

            if project not in projects:
                raise InvalidProjectError(
                    "No project found with name '{}'.".format(project))
            else:
                try:
                    self.project_store[project] = Project(
                        self.component_builder, project,
                        self.project_dir, self.remote_storage)
                except Exception as e:
                    raise InvalidProjectError(
                        "Unable to load project '{}'. "
                        "Error: {}".format(project, e))

        time = data.get('time')
        response = self.project_store[project].parse(data['text'], time,
                                                     model, request_params=request_params)

        if self.responses:
            self.responses.info('', user_input=response, project=project,
                                model=response.get('model'))

        return self.format_response(response)
