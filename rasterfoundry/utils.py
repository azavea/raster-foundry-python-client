from future.standard_library import install_aliases  # noqa
install_aliases()  # noqa
from urllib.parse import urlparse
from os.path import join
import tempfile
import uuid
import json
import os
import errno

import boto3

from .settings import RV_CPU_JOB_DEF, RV_CPU_QUEUE, DEVELOP_BRANCH


class RasterVisionBatchClient():
    def __init__(self, job_queue=RV_CPU_QUEUE, job_definition=RV_CPU_JOB_DEF,
                 branch_name=DEVELOP_BRANCH, attempts=1):
        """Create a Raster Vision Batch Client

        Args:
            job_queue (str): name of the Batch job queue to run the job in
            job_definition (str): name of the Batch job definition
            branch_name (str): branch of the raster-vision repo to use
            attempts (int): number of attempts for each job
        """

        self.job_queue = job_queue
        self.job_definition = job_definition
        self.branch_name = branch_name
        self.attempts = attempts
        self.batch_client = boto3.client('batch')

    def start_raster_vision_job(self, job_name, command):
        """Start a raster-vision Batch job.

        Args:
            job_name (str): name of the Batch job
            command (str): command to run inside the Docker container

        Returns:
            job_id (str): job_id of job started on Batch
        """
        # `run_script.sh $branch_name $command` downloads a branch of the
        # raster-vision repo and then runs the command.
        job_command = ['run_script.sh', self.branch_name, command]
        job_id = self.batch_client.submit_job(
            jobName=job_name, jobQueue=self.job_queue,
            jobDefinition=self.job_definition,
            containerOverrides={
                'command': job_command
            },
            retryStrategy={
                'attempts': self.attempts
            })['jobId']

        return job_id


def upload_raster_vision_config(config_dict, config_uri_root):
    """Upload a config file to S3

    Args:
        config_dict: a dictionary to turn into a JSON file to upload
        config_uri_root: the root of the URI to upload the config to

    Returns:
        remote URI of the config file generate using a UUID
    """
    with tempfile.NamedTemporaryFile('w') as config_file:
        json.dump(config_dict, config_file)
        config_uri = join(
            config_uri_root, '{}.json'.format(uuid.uuid1()))
        s3 = boto3.resource('s3')
        parsed_uri = urlparse(config_uri)
        # Rewind file to beginning so that full content will be loaded.
        # Without this line 0 bytes are uploaded.
        config_file.seek(0)
        s3.meta.client.upload_file(
            config_file.name, parsed_uri.netloc, parsed_uri.path[1:])

        return config_uri


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
