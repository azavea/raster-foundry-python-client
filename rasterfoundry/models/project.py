"""A Project is a collection of zero or more scenes"""
from .. import NOTEBOOK_SUPPORT

if NOTEBOOK_SUPPORT:
    from ipyleaflet import (
        Map,
        SideBySideControl,
        TileLayer,
    )

from ..decorators import check_notebook  # NOQA
from .map_token import MapToken


class Project(object):
    """A Raster Foundry project"""

    TILE_PATH_TEMPLATE = '/tiles/{id}/{{z}}/{{x}}/{{y}}/'

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

    @check_notebook
    def get_layer(self):
        """Returns a TileLayer for display using ipyleaflet"""
        return TileLayer(url=self.tms())

    def get_map_token(self):
        """Returns the map token for this project

        Returns:
            str
        """

        resp = (
            self.api.client.Imagery.get_map_tokens(projectId=self.id).result()
        )
        if resp.results:
            return MapToken(resp.results[0], self.api)

    def tms(self):
        """Return a TMS URL for a project"""

        tile_path = self.TILE_PATH_TEMPLATE.format(id=self.id)
        return '{scheme}://{host}{tile_path}'.format(
            scheme=self.api.scheme, host=self.api.tile_host,
            tile_path=tile_path
        )
