"""An Upload is raw data to be transformed into a Scene"""
import glob
import os

import boto3


class Upload(object):
    """A Raster Foundry upload"""

    s3_client = boto3.client('s3')

    def __repr__(self):
        return '<Upload - {}>'.format(self.name)

    def __init__(self, upload, api):
        """Instantiate a new Upload

        Args:
            upload (Upload): generated Upload object from specification
            api (API): api used to make requests on behalf of an upload
        """

        self._upload = upload
        self.api = api

        self.id = upload.id
        self.upload_type = upload.uploadType
        self.metadata = upload.metadata
        self.files = upload.files

    @classmethod
    def upload_create_from_files(
            cls, datasource, organization, paths_to_tifs,
            dest_bucket, dest_prefix, metadata={}, visibility='PRIVATE',
            project_id=None, dry_run=False
    ):
        """Create an Upload from a set of tifs

        Args:
            datasource (str): UUID of the datasource this upload belongs to
            organization (str): UUID of the organization this upload belongs to
            paths_to_tifs (str | str[]): which tifs to upload. If passed a
                string, files will be the unix path expansion of the passed
                string, e.g., '*.tif' will become an array of all of the tifs
                in the current working directory. If passed a list, files will
                be exactly those files in the list.
            dest_bucket (str): s3 bucket to upload local files to. If the
                Raster Foundry application does not have permission to read
                from this location, the upload will fail to process.
            dest_prefix (str): s3 prefix to upload local files to. If the
                Raster Foundry application does not have permission to read
                from this location, the upload will fail to process.
            metadata (dict): Additional information to store with this upload.
                acquisitionDate and cloudCover will be parsed into any created
                scenes.
            visibility (str): PUBLIC, PRIVATE, or ORGANIZATION visibility level
                for the created scenes
            project_id (str): UUID of the project scenes from this upload
                should be added to
            dry_run (bool): whether to perform side-effecting actions like
                uploads to s3

        Returns:
            dict: splattable object to post to /uploads/
        """
        if isinstance(paths_to_tifs, str):
            paths = glob.glob(paths_to_tifs)
        else:
            paths = paths_to_tifs
        upload_status = 'UPLOADED'
        file_type = 'GEOTIFF'

        files = []
        for f in paths:
            fname = os.path.split(f)[-1]
            key = '/'.join([x for x in [dest_prefix, fname] if x])
            dest_path = 's3://' + '/'.join(
                [x for x in [dest_bucket, dest_prefix, fname] if x]
            )
            if not dry_run:
                with open(f, 'r') as inf:
                    cls.s3_client.put_object(
                        Body=inf.read(),
                        Bucket=dest_bucket,
                        Key=key
                    )
            files.append(dest_path)

        return dict(
            uploadStatus=upload_status,
            files=files,
            uploadType='S3',
            fileType=file_type,
            datasource=datasource,
            organizationId=organization,
            metadata=metadata,
            visibility=visibility,
            projectId=project_id
        )

    @classmethod
    def create(cls, api, upload_create):
        """Post an upload to Raster Foundry for processing

        Args:
            api (API): API to use for requests
            upload_create (dict): post parameters for /uploads. See
                upload_create_from_files

        Returns:
            Upload: created object in Raster Foundry
        """

        return api.client.Imagery.post_uploads(Upload=upload_create).result()
