import setuptools

setuptools.setup(
    name="rasterfoundry",
    version="0.4.0",
    description='A Python client for Raster Foundry, a web platform for '
    'combining, analyzing, and publishing raster data.',
    long_description=open('README.rst').read(),
    url='https://github.com/raster-foundry/raster-foundry-python-client',
    author='Raster Foundry',
    author_email='info@rasterfoundry.com',
    license='Apache License 2.0',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    keywords='raster earth-observation geospatial geospatial-processing',
    packages=setuptools.find_packages(exclude=['tests']),
    package_data={'': ['*.yml']},
    install_requires=[
        'cryptography >= 2.0.0',
        'pyasn1 >= 0.2.3',
        'requests >= 2.9.1',
        'bravado >= 8.4.0',
        'boto3 >= 1.4.4'
    ],
    extras_require={
        'notebook': [
            'notebook >= 4.0.0',
            'ipyleaflet==0.4.0a1'
        ],
        'dev': [],
        'test': [],
    },
    tests_require=[],
    dependency_links=[
        'https://github.com/azavea/ipyleaflet/tarball/0.4.0a/'
    ]
)
