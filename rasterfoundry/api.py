import json
import os
import uuid

from bravado.client import SwaggerClient
from bravado.requests_client import RequestsClient
from bravado.swagger_model import load_file, load_url
from simplejson import JSONDecodeError


from .aws.s3 import str_to_file
from .exceptions import RefreshTokenException
from .models import Analysis, MapToken, Project, Export
from .settings import RV_TEMP_URI

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


SPEC_PATH = os.getenv(
    'RF_API_SPEC_PATH',
    'https://raw.githubusercontent.com/raster-foundry/raster-foundry-api-spec/1.4.0/spec/spec.yml'
)


class API(object):
    """Class to interact with Raster Foundry API"""

    def __init__(self, refresh_token=None, api_token=None,
                 host='app.rasterfoundry.com', scheme='https'):
        """Instantiate an API object to make requests to Raster Foundry's REST API

        Args:
            refresh_token (str): optional token used to obtain an API token to
                                 make API requests
            api_token (str): optional token used to authenticate API requests
            host (str): optional host to use to make API requests against
            scheme (str): optional scheme to override making requests with
        """

        self.http = RequestsClient()
        self.scheme = scheme

        if urlparse(SPEC_PATH).netloc:
            spec = load_url(SPEC_PATH)
        else:
            spec = load_file(SPEC_PATH)

        self.app_host = host
        spec['host'] = host
        spec['schemes'] = [scheme]

        split_host = host.split('.')
        split_host[0] = 'tiles'
        self.tile_host = '.'.join(split_host)

        config = {'validate_responses': False}
        self.client = SwaggerClient.from_spec(spec, http_client=self.http,
                                              config=config)

        if refresh_token and not api_token:
            api_token = self.get_api_token(refresh_token)
        elif not api_token:
            raise Exception('Must provide either a refresh token or API token')

        self.api_token = api_token
        self.http.session.headers['Authorization'] = 'Bearer {}'.format(
            api_token)

    def get_api_token(self, refresh_token):
        """Retrieve API token given a refresh token

        Args:
            refresh_token (str): refresh token used to make a request for a new
                                 API token

        Returns:
            str
        """
        post_body = {'refresh_token': refresh_token}

        try:
            response = self.client.Authentication.post_tokens(
                refreshToken=post_body).future.result()
            return response.json()['id_token']
        except JSONDecodeError:
            raise RefreshTokenException('Error using refresh token, please '
                                        'verify it is valid')

    @property
    def map_tokens(self):
        """List map tokens a user has access to

        Returns:
            List[MapToken]
        """

        has_next = True
        page = 0
        map_tokens = []
        while has_next:
            paginated_map_tokens = (
                self.client.Imagery.get_map_tokens(page=page).result()
            )
            map_tokens += [
                MapToken(map_token, self)
                for map_token in paginated_map_tokens.results
            ]
            page = paginated_map_tokens.page + 1
            has_next = paginated_map_tokens.hasNext
        return map_tokens

    @property
    def projects(self):
        """List projects a user has access to

        Returns:
            List[Project]
        """
        has_next = True
        projects = []
        page = 0
        while has_next:
            paginated_projects = self.client.Imagery.get_projects(
                page=page).result()
            has_next = paginated_projects.hasNext
            page = paginated_projects.page + 1
            for project in paginated_projects.results:
                projects.append(Project(project, self))
        return projects

    @property
    def analyses(self):
        """List analyses a user has access to

        Returns:
            List[Analysis]
        """
        has_next = True
        analyses = []
        page = 0
        while has_next:
            paginated_analyses = self.client.Lab.get_tool_runs(page=page).result()
            has_next = paginated_analyses.hasNext
            page = paginated_analyses.page + 1
            for analysis in paginated_analyses.results:
                analyses.append(Analysis(analysis, self))
        return analyses

    @property
    def exports(self):
        """List exports a user has access to

        Returns:
            List[Export]
        """
        has_next = True
        page = 0
        exports = []
        while has_next:
            paginated_exports = self.client.Imagery.get_exports(page=page).result()
            has_next = paginated_exports.hasNext
            page = paginated_exports.page + 1
            for export in paginated_exports.results:
                exports.append(Export(export, self))
        return exports

    def get_datasources(self, **kwargs):
        return self.client.Datasources.get_datasources(**kwargs).result()

    def get_scenes(self, **kwargs):
        bbox = kwargs.get('bbox')
        if bbox and hasattr(bbox, 'bounds'):
            kwargs['bbox'] = ','.join(str(x) for x in bbox.bounds)
        elif bbox and type(bbox) != type(','.join(str(x) for x in bbox)): # NOQA
            kwargs['bbox'] = ','.join(str(x) for x in bbox)
        return self.client.Imagery.get_scenes(**kwargs).result()

    def get_project_config(self, project_ids, annotations_uris=None):
        """Get data needed to create project config file for prep_train_data

        The prep_train_data script requires a project config files which
        lists the images and annotation URIs associated with each project
        that will be used to generate training data. If the annotation_uris
        are not specified, an annotation file for each project will be
        generated and saved to S3.

        Args:
            project_ids: list of project ids to make training data from
            annotations_uris: optional list of corresponding annotation URIs

        Returns:
            Object of form [{'images': [...], 'annotations':...}, ...]
        """
        project_configs = []
        for project_ind, project_id in enumerate(project_ids):
            proj = Project(
                self.client.Imagery.get_projects_uuid(uuid=project_id).result(),
                self)

            if annotations_uris is None:
                annotations_uri = os.path.join(
                    RV_TEMP_URI, 'annotations', '{}.json'.format(uuid.uuid4()))
                proj.save_annotations_json(annotations_uri)
            else:
                annotations_uri = annotations_uris[project_ind]

            image_uris = proj.get_image_source_uris()
            project_configs.append({
                'id': project_id,
                'images': image_uris,
                'annotations': annotations_uri
            })

        return project_configs

    def save_project_config(self, project_ids, output_uri,
                            annotations_uris=None):
        """Save project config file.

        This file is needed by Raster Vision to prepare training data, make
        predictions, and evaluate predictions.

        Args:
            project_ids: list of project ids to make training data from
            output_path: where to write the project config file
            annotations_uris: optional list of corresponding annotation URIs
        """
        project_config = self.get_project_config(
            project_ids, annotations_uris)
        project_config_str = json.dumps(
            project_config, sort_keys=True, indent=4)

        str_to_file(project_config_str, output_uri)
