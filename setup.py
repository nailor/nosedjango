import os
from setuptools import setup, find_packages

# This reads the current version from nosedjango's __init__.py
execfile(os.path.join(os.path.dirname(__file__), 'nosedjango/__init__.py'))

setup(
    name='NoseDjango',
    version='.'.join(str(x) for x in __version__),
    author='Jyrki Pulliainen',
    author_email='jyrki.pulliainen@inoi.fi',
    description='nose plugin for easy testing of django projects ' \
        'and apps. Sets up a test database (or schema) and installs apps ' \
        'from test settings file before tests are run, and tears the test ' \
        'database (or schema) down after all tests are run.',
    install_requires='nose>=0.10',
    url="http://www.assembla.com/spaces/nosedjango",
    license='GNU LGPL',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    entry_points={
        'nose.plugins': [
            'django=nosedjango.nosedjango:NoseDjango',
            ]
        }
    )
