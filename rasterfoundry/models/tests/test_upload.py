import os
import shutil
import random
from string import ascii_letters


import pytest


from ..upload import Upload


@pytest.fixture
def datasource():
    return 'fooDat'


@pytest.fixture
def organization():
    return 'fooOrg'


@pytest.fixture
def random_tifs():
    return [
        ''.join([random.choice(ascii_letters) for _ in range(10)]) + '.tif'
        for _ in range(10)
    ]


@pytest.fixture
def bogus_bucket():
    return 'fooBucket'


@pytest.fixture
def bogus_prefix():
    return 'fooPrefix'


def test_file_globbing(datasource, organization, random_tifs, bogus_bucket,
                       bogus_prefix):
    tifs = os.path.join('/tmp', 'tifs')
    other_tifs = os.path.join('/tmp', 'other_tifs')
    os.mkdir(tifs)
    os.mkdir(other_tifs)
    paths = []
    for i, t in enumerate(random_tifs):
        if i % 2 == 0:
            out_path = os.path.join(tifs, t)
        else:
            out_path = os.path.join(other_tifs, t)
        with open(out_path, 'w') as outf:
            outf.write('a tif')
            paths.append(out_path)

    upload_create = Upload.upload_create_from_files(
        datasource, organization, '/tmp/**/*.tif', bogus_bucket, bogus_prefix,
        dry_run=True
    )
    upload_fnames = [os.path.split(f)[-1] for f in upload_create['files']]
    src_fnames = [os.path.split(f)[-1] for f in paths]
    assert set(upload_fnames) == set(src_fnames)

    shutil.rmtree(tifs)
    shutil.rmtree(other_tifs)


def test_no_file_globbing(datasource, organization, bogus_bucket,
                          bogus_prefix):
    files = ['bar.tif', 'foo.tif']
    upload_create = Upload.upload_create_from_files(
        datasource, organization, files, bogus_bucket, bogus_prefix,
        dry_run=True
    )

    upload_fnames = [os.path.split(f)[-1] for f in upload_create['files']]
    assert upload_fnames == files
