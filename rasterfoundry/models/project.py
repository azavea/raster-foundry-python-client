"""A Project is a collection of zero or more scenes"""
import copy
import json
import uuid
from datetime import date, datetime

import requests

from .export import Export
from .map_token import MapToken
from .. import NOTEBOOK_SUPPORT
from ..aws.s3 import file_to_str, str_to_file
from ..decorators import check_notebook
from ..exceptions import GatewayTimeoutException
from ..utils import get_all_paginated

if NOTEBOOK_SUPPORT:
    from ipyleaflet import (
        Map,
        SideBySideControl,
        TileLayer,
    )


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
        return api.client.Imagery.post_projects(project=project_create)

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

    def get_thumbnail(self, bbox, zoom, export_format, raw):
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
            params={
                'bbox': bbox,
                'zoom': zoom,
                'token': self.api.api_token,
                'colorCorrect': 'false' if raw else 'true'
            },
            headers=headers
        )
        if response.status_code == requests.codes.gateway_timeout:
            raise GatewayTimeoutException(
                'The export request timed out. '
                'Try decreasing the zoom level or using a smaller bounding box.'
            )
        response.raise_for_status()
        return response

    def create_export(self, bbox, zoom=10, raster_size=4000):
        """Create an export job for this project

        Args:
            bbox (str): Bounding box (formatted as 'x1,y1,x2,y2') for the download
            zoom (int): Zoom level for the download
            raster_size (int): desired tiff size after export, 4000 by default - same as backend

        Returns:
            Export
        """
        return Export.create_export(
            self.api, bbox=bbox, zoom=zoom, project=self, raster_size=raster_size)

    def geotiff(self, bbox, zoom=10, raw=False):
        """Download this project as a geotiff

        The returned string is the raw bytes of the associated geotiff.

        Args:
            bbox (str): Bounding box (formatted as 'x1,y1,x2,y2') for the download
            zoom (int): zoom level for the export

        Returns:
            str
        """

        return self.get_thumbnail(bbox, zoom, 'tiff', raw).content

    def png(self, bbox, zoom=10, raw=False):
        """Download this project as a png

        The returned string is the raw bytes of the associated png.

        Args:
            bbox (str): Bounding box (formatted as 'x1,y1,x2,y2') for the download
            zoom (int): zoom level for the export

        Returns
            str
        """

        return self.get_thumbnail(bbox, zoom, 'png', raw).content

    def tms(self):
        """Return a TMS URL for a project"""

        tile_path = self.TILE_PATH_TEMPLATE.format(id=self.id)
        return '{scheme}://{host}{tile_path}?token={token}'.format(
            scheme=self.api.scheme, host=self.api.tile_host,
            tile_path=tile_path, token=self.api.api_token
        )

    def post_annotations(self, annotations_uri):
        annotations = json.loads(file_to_str(annotations_uri))
        # Convert RV annotations to RF format.
        rf_annotations = copy.deepcopy(annotations)
        for feature in rf_annotations['features']:
            properties = feature['properties']
            feature['properties'] = {
                'label': properties['class_name'],
                'description': '',
                'machineGenerated': True,
                'confidence': properties['score']
            }

        self.api.client.Imagery.post_projects_projectID_annotations(
            projectID=self.id, annotations=rf_annotations).future.result()

    def get_annotations(self):
        def get_page(page):
            return self.api.client.Imagery.get_projects_projectID_annotations(
                projectID=self.id, page=page).result()

        return get_all_paginated(get_page, list_field='features')

    def save_annotations_json(self, output_uri):
        features = self.get_annotations()
        geojson = {'features': [feature._as_dict() for feature in features]}

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code."""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError('Type {} not serializable'.format(str(type(obj))))

        geojson_str = json.dumps(geojson, default=json_serial)
        str_to_file(geojson_str, output_uri)

    def get_scenes(self):
        def get_page(page):
            return self.api.client.Imagery.get_projects_projectID_scenes(
                projectID=self.id, page=page).result()

        return get_all_paginated(get_page)

    def get_ordered_scene_ids(self):
        def get_page(page):
            return self.api.client.Imagery.get_projects_projectID_order(
                projectID=self.id, page=page).result()

        # Need to reverse so that order is from bottom-most to top-most layer.
        return list(reversed(get_all_paginated(get_page)))

    def get_image_source_uris(self):
        """Return sourceUris of images for with this project sorted by z-index."""
        source_uris = []

        scenes = self.get_scenes()
        ordered_scene_ids = self.get_ordered_scene_ids()

        id_to_scene = {}
        for scene in scenes:
            id_to_scene[scene.id] = scene
        sorted_scenes = [id_to_scene[scene_id] for scene_id in ordered_scene_ids]

        for scene in sorted_scenes:
            for image in scene.images:
                source_uris.append(image.sourceUri)

        return source_uris

    def start_predict_job(self, rv_batch_client, inference_graph_uri,
                          label_map_uri, predictions_uri,
                          channel_order=[0, 1, 2]):
        """Start a Batch job to perform object detection on this project.

        Args:
            rv_batch_client: instance of RasterVisionBatchClient used to start
                Batch jobs
            inference_graph_uri (str): file with exported object detection
                model file
            label_map_uri (str): file with mapping from class id to display name
            predictions_uri (str): GeoJSON file output by the prediction job
            channel_order (list of int)
        Returns:
            job_id (str): job_id of job started on Batch
        """
        source_uris = self.get_image_source_uris()
        source_uris_str = ' '.join(source_uris)
        channel_order = ' '.join([str(channel) for channel in channel_order])
        # Add uuid to job_name because it has to be unique.
        job_name = 'predict_project_{}_{}'.format(self.id, uuid.uuid1())
        command = 'python -m rv.detection.run predict --channel-order {} {} {} {} {}'.format(  # noqa
            channel_order, inference_graph_uri, label_map_uri, source_uris_str,
            predictions_uri)
        job_id = rv_batch_client.start_raster_vision_job(job_name, command)

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
