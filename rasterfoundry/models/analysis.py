"""An Analysis is a set of operations which take projects as inputs and output raster imagery"""
import requests

from .. import NOTEBOOK_SUPPORT
from .export import Export
from .project import Project
from ..decorators import check_notebook
from ..exceptions import GatewayTimeoutException

if NOTEBOOK_SUPPORT:
    from ipyleaflet import (
        Map,
        SideBySideControl,
        TileLayer,
    )


class Analysis(object):
    """A Raster Foundry Analysis"""

    TILE_PATH_TEMPLATE = '/tools/{id}/{{z}}/{{x}}/{{y}}/'
    EXPORT_TEMPLATE = '/tools/{analysis}/raw/'

    def __repr__(self):
        return'<Analysis - {}>'.format(self.name)

    def __init__(self, analysis, api):
        """Instantiate a new Analysis

        Args:
            analysis (Analysis): generated Analysis object from specification
            api (API): api used to make requests on behalf of the analysis
        """
        self._analysis = analysis
        self.api = api

        self.name = analysis.name
        self.id = analysis.id

    def get_thumbnail(self, bbox, zoom, raw=False):
        export_path = self.EXPORT_TEMPLATE.format(analysis=self.id)
        request_path = '{scheme}://{host}{export_path}'.format(
            scheme=self.api.scheme, host=self.api.tile_host, export_path=export_path
        )

        response = requests.get(
            request_path,
            params={
                'bbox': bbox,
                'zoom': zoom,
                'token': self.api.api_token,
                'colorCorrect': 'false' if raw else 'true'
            }
        )
        if response.status_code == requests.codes.gateway_timeout:
            raise GatewayTimeoutException(
                'The export request timed out. '
                'Try decreasing the zoom level or using a smaller bounding box.'
            )
        response.raise_for_status()
        return response

    def create_export(self, bbox, zoom=10, **exportOpts):
        """Download this Analysis as a single band tiff

        Args:
            bbox (str): Bounding box(formatted as 'x1,y1,x2,y2') for the download
            zoom (int): Zoom level for the download
            exportOpts (dict): Additional parameters to pass to an async export job

        Returns:
            Export
        """
        return Export.create_export(self.api, bbox=bbox, zoom=zoom, analysis=self, **exportOpts)

    def tms(self, node=None):
        """Returns a TMS URL for this project

        Args:
            node (string): UUID for the node to view, defaulting to the full analysis

        Returns:
            str
        """
        tile_path = self.TILE_PATH_TEMPLATE.format(id=self.id)
        return '{scheme}://{host}{tile_path}?token={token}'.format(
            scheme=self.api.scheme, host=self.api.tile_host,
            tile_path=tile_path, token=self.api.api_token
        )

    @check_notebook
    def get_layer(self):
        """Returns a TileLayer for display using ipyleaflet"""
        return TileLayer(url=self.tms())

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
    def add_to(self, leaflet_map):
        """Add this project to a leaflet map

        Args:
            leaflet_map (Map): map to add this layer to
        """

        leaflet_map.add_layer(self.get_layer())

    @check_notebook
    def get_map(self, **kwargs):
        """Return an ipyleaflet map centered at the analysis's center

        Args:
            **kwargs: additional arguments to pass to map initializations
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

    def get_inputs(self):
        """Get the input nodes for the analysis"""
        dag_root = self._analysis.executionParameters
        nodes = [dag_root]
        inputs = []
        while len(nodes) > 0:
            current = nodes.pop()
            args = current.get('args')
            if current.get('type') == 'projectSrc':
                inputs.append(current)
            if type(args) == list:
                for arg in args:
                    nodes.append(arg)
        return inputs

    def get_center(self):
        """Get the center of this analysis's first input's extent"""

        # get analysis input UUIDS
        inputs = self.get_inputs()
        if len(inputs) > 0:
            # fetch first one from api and use that project's coordinates
            input = inputs.pop()
            project = Project(
                self.api.client.Imagery.get_projects_projectID(
                    projectID=input.get('projId')
                ).result(),
                self.api
            )
            return project.get_center()
        else:
            raise ValueError('An analysis must have inputs in order to be valid')
