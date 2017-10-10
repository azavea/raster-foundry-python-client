"""A Project is a collection of zero or more scenes"""
import requests
import uuid

import boto3

from .. import NOTEBOOK_SUPPORT
from ..decorators import check_notebook
from ..exceptions import GatewayTimeoutException
from .map_token import MapToken

if NOTEBOOK_SUPPORT:
    from ipyleaflet import (
        Map,
        SideBySideControl,
        TileLayer,
    )

RV_CPU_QUEUE = 'raster-vision-cpu'
RV_CPU_JOB_DEF = 'raster-vision-cpu'
DEVELOP_BRANCH = 'develop'


def start_raster_vision_job(job_name, command, job_queue=RV_CPU_QUEUE,
                            job_definition=RV_CPU_JOB_DEF,
                            branch_name=DEVELOP_BRANCH, attempts=1):
    """Start a raster-vision Batch job.

    Args:
        job_name (str): name of the Batch job
        command (str): command to run inside the Docker container
        job_queue (str): name of the Batch job queue to run the job in
        job_definition (str): name of the Batch job definition
        branch_name (str): branch of the raster-vision repo to use
        attempts (int): number of attempts for the Batch job

    Returns:
        job_id (str): job_id of job started on Batch
    """
    batch_client = boto3.client('batch')
    # `run_script.sh $branch_name $command` downloads a branch of the
    # raster-vision repo and then runs the command.
    job_command = ['run_script.sh', branch_name, command]
    job_id = batch_client.submit_job(
        jobName=job_name, jobQueue=job_queue, jobDefinition=job_definition,
        containerOverrides={
            'command': job_command
        },
        retryStrategy={
            'attempts': attempts
        })['jobId']

    return job_id


class Project(object):
    """A Raster Foundry project"""

    TILE_PATH_TEMPLATE = '/tiles/{id}/{{z}}/{{x}}/{{y}}/'
    EXPORT_TEMPLATE = '/tiles/{project}/export/'

    def __repr__(self):
        return '<Project - {}>'.format(self.name)

    def __init__(self, project, api):
        """Instantiate a new Project

        Args:
            project (Project): generated Project objects from specification
            api (API): api used to make requests on behalf of a project
        """
        self._project = project
        self.api = api

        # A few things we care about
        self.name = project.name
        self.id = project.id

    @classmethod
    def create(cls, api, project_create):
        """Post a project to Raster Foundry

        Args:
            api (API): API to use for requests
            project_create (dict): post parameters for /projects. See
                project_create

        Returns:
            Project: created object in Raster Foundry
        """
        return api.client.Imagery.post_projects(project_create)

    def get_center(self):
        """Get the center of this project's extent"""
        coords = self._project.extent.get('coordinates')
        if not coords:
            raise ValueError(
                'Project must have coordinates to calculate a center'
            )
        x_min = min(
            coord[0] + (360 if coord[0] < 0 else 0) for coord in coords[0]
        )
        x_max = max(
            coord[0] + (360 if coord[0] < 0 else 0) for coord in coords[0]
        )
        y_min = min(coord[1] for coord in coords[0])
        y_max = max(coord[1] for coord in coords[0])
        center = [(y_min + y_max) / 2., (x_min + x_max) / 2.]
        if center[0] > 180:
            center[0] = center[0] - 360
        return tuple(center)

    def get_map_token(self):
        """Returns the map token for this project

        Returns:
            str
        """

        resp = (
            self.api.client.Imagery.get_map_tokens(project=self.id).result()
        )
        if resp.results:
            return MapToken(resp.results[0], self.api)

    def get_export(self, bbox, zoom=10, export_format='png'):
        """Download this project as a file

        PNGs will be returned if the export_format is anything other than tiff

        Args:
            bbox (str): Bounding box (formatted as 'x1,y1,x2,y2') for the download
            export_format (str): Requested download format

        Returns:
            str
        """

        headers = self.api.http.session.headers.copy()
        headers['Accept'] = 'image/{}'.format(
            export_format
            if export_format.lower() in ['png', 'tiff']
            else 'png'
        )
        export_path = self.EXPORT_TEMPLATE.format(project=self.id)
        request_path = '{scheme}://{host}{export_path}'.format(
            scheme=self.api.scheme, host=self.api.tile_host,
            export_path=export_path
        )

        response = requests.get(
            request_path,
            params={'bbox': bbox, 'zoom': zoom, 'token': self.api.api_token},
            headers=headers
        )
        if response.status_code == requests.codes.gateway_timeout:
            raise GatewayTimeoutException(
                'The export request timed out. '
                'Try decreasing the zoom level or using a smaller bounding box.'
            )
        response.raise_for_status()
        return response

    def geotiff(self, bbox, zoom=10):
        """Download this project as a geotiff

        The returned string is the raw bytes of the associated geotiff.

        Args:
            bbox (str): Bounding box (formatted as 'x1,y1,x2,y2') for the download
            zoom (int): zoom level for the export

        Returns:
            str
        """

        return self.get_export(bbox, zoom, 'tiff').content

    def png(self, bbox, zoom=10):
        """Download this project as a png

        The returned string is the raw bytes of the associated png.

        Args:
            bbox (str): Bounding box (formatted as 'x1,y1,x2,y2') for the download
            zoom (int): zoom level for the export

        Returns
            str
        """

        return self.get_export(bbox, zoom, 'png').content

    def tms(self):
        """Return a TMS URL for a project"""

        tile_path = self.TILE_PATH_TEMPLATE.format(id=self.id)
        return '{scheme}://{host}{tile_path}?token={token}'.format(
            scheme=self.api.scheme, host=self.api.tile_host,
            tile_path=tile_path, token=self.api.api_token
        )

    def get_image_source_uris(self):
        """Return the sourceUris of images associated with this project"""
        source_uris = []
        scenes = self.api.client.Imagery.get_projects_uuid_scenes(uuid=self.id) \
                     .result().results
        for scene in scenes:
            for image in scene.images:
                source_uris.append(image.sourceUri)

        return source_uris

    def start_predict_job(self, inference_graph_uri, label_map_uri,
                          predictions_uri, job_queue=RV_CPU_QUEUE,
                          job_definition=RV_CPU_JOB_DEF,
                          branch_name=DEVELOP_BRANCH, attempts=1):
        """Start a Batch job to perform object detection on this project.

        Args:
            inference_graph_uri (str): file with exported object detection
                model file
            label_map_uri (str): file with mapping from class id to display name
            predictions_uri (str): GeoJSON file output by the prediction job
            job_queue (str): name of the Batch job queue to run the job in
            job_definition (str): name of the Batch job definition
            branch_name (str): branch of the raster-vision repo to use
            attempts (int): number of attempts for the Batch job

        Returns:
            job_id (str): job_id of job started on Batch
        """
        source_uris = self.get_image_source_uris()
        source_uris_str = ' '.join(source_uris)

        # Add uuid to job_name because it has to be unique.
        job_name = 'predict_project_{}_{}'.format(self.id, uuid.uuid1())
        command = 'python -m rv.run predict {} {} {} {}'.format(
            inference_graph_uri, label_map_uri, source_uris_str,
            predictions_uri)
        job_id = start_raster_vision_job(
            job_name, command, job_queue=job_queue,
            job_definition=job_definition, branch_name=branch_name,
            attempts=attempts)

        return job_id

    @check_notebook
    def add_to(self, leaflet_map):
        """Add this project to a leaflet map

        Args:
            leaflet_map (Map): map to add this layer to
        """

        leaflet_map.add_layer(self.get_layer())

    @check_notebook
    def compare(self, other, leaflet_map):
        """Add a slider to compare two projects

        This project determines the map center.

        Args:
            other (Project): the project to compare with this project
            leaflet_map (Map): map to add the slider to
        """

        control = SideBySideControl(
            leftLayer=self.get_layer(), rightLayer=other.get_layer()
        )
        leaflet_map.add_control(control)

    @check_notebook
    def get_layer(self):
        """Returns a TileLayer for display using ipyleaflet"""
        return TileLayer(url=self.tms())

    @check_notebook
    def get_map(self, **kwargs):
        """Return an ipyleaflet map centered on this project's center

        Args:
            **kwargs: additional arguments to pass to Map initializations
        """
        default_url = (
            'https://cartodb-basemaps-{s}.global.ssl.fastly.net/'
            'light_all/{z}/{x}/{y}.png'
        )
        return Map(
            default_tiles=TileLayer(url=kwargs.get('url', default_url)),
            center=self.get_center(),
            scroll_wheel_zoom=kwargs.get('scroll_wheel_zoom', True),
            **kwargs
        )
