from future.standard_library import install_aliases  # noqa
install_aliases()  # noqa
from urllib.parse import urlparse
from os.path import join
import tempfile
import uuid
import json

import boto3


def start_raster_vision_job(job_name, command, job_queue, job_definition,
                            branch_name, attempts=1):
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
