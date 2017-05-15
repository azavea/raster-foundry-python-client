class MapToken(object):
    """A Raster Foundry map token"""

    def __repr__(self):
        return '<MapToken - {} - {}>'.format(self.project.name, self.token)

    def __init__(self, map_token, api):
        """Instantiate a new MapToken

        Args:
            map_token (MapToken): generated MapToken object from specification
            api (API): api  used to make requests
        """

        self._map_token = map_token
        self.api = api

        # A few things we care about
        self.token = map_token.id
        self.last_modified = map_token.modifiedAt
        self.project = [
            proj for proj in self.api.projects if proj.id == map_token.project
        ].pop()
