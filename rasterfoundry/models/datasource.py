"""A Datasource is a source of data a scene uses"""


class Datasource(object):
    """A Raster Foundry datasource"""

    def __repr__(self):
        return '<Datasource - {}>'.format(self.name)

    def __init__(self, datasource, api):
        """Instantiate a new Datasource

        Args:
            datasource (Datasource): generated Datasource object from specification
            api (API): api used to make requests on behalf of a datasource
        """
        self._datasource = datasource
        self.api = api

        # A few things we care about
        self.name = datasource.name
        self.id = datasource.id

    @classmethod
    def create_datasource_band(cls, name, number, wavelength):
        """Create a datasource band

        Args:
            name (str): name of band, e.g. 'read', 'blue', 'infrared', etc.
            number (str): band number
            wavelength (str): wavelength

        Returns:
            dict: a band definition of a datasource band
        """
        return dict(
            name=name,
            number=number,
            wavelength=wavelength
        )

    @classmethod
    def create(cls, api, name, bands, visibility='PRIVATE', extras={}):
        """Post an upload to Raster Foundry for processing

        Args:
            api (API): API to use for requests
            name (str): name of datasource
            bands (array): an array of create_datasource_band
            visibility (str): datasource visibility, 'PRIVATE' by default
            extras (dict): additional related information for a datasource, {} by default

        Returns:
            Datasource: created datasource object in Raster Foundry
        """
        datasource_created = dict(
            name=name,
            bands=bands,
            visibility=visibility,
            extras=extras,
            composites={
                'natural': {
                    'label': 'Default',
                    'value': {
                        'redBand': 0,
                        'greenBand': 1,
                        'blueBand': 2
                    }
                }
            }
        )
        return api.client.Datasources.post_datasources(datasource=datasource_created).result()

    @classmethod
    def update(cls, api, datasource_id, datasource):
        return api.client.Datasources.put_datasources_datasourceID(
            datasourceID=datasource_id, datasource=datasource).result()

    @classmethod
    def delete(cls, api, datasource_id):
        return api.client.Datasources.delete_datasources_datasourceID(
            datasourceID=datasource_id).result()
