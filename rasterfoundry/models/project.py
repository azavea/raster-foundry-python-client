"""A Project is a collection of zero or more scenes"""
import requests

from .. import NOTEBOOK_SUPPORT
from ..decorators import check_notebook
from .map_token import MapToken

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
            bbox (str): GeoJSON format bounding box for the download
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

        return requests.get(
            request_path,
            params={'bbox': bbox, 'zoom': zoom, 'token': self.api.api_token},
            headers=headers
        )

    def geotiff(self, bbox, zoom=10):
        """Download this project as a geotiff

        The returned string is the raw bytes of the associated geotiff.

        Args:
            bbox (str): GeoJSON format bounding box for the download
            zoom (int): zoom level for the export

        Returns:
            str
        """

        return self.get_export(bbox, zoom, 'tiff').content

    def png(self, bbox, zoom=10):
        """Download this project as a png

        The returned string is the raw bytes of the associated png.

        Args:
            bbox (str): GeoJSON format bounding box for the download
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
