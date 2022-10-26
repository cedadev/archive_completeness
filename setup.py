# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='archive_completeness',
    version='0.0.1',
    description='find catalogue coverage in FBI',
    long_description=long_description,

    # The project's main homepage.
    url='http://www.ceda.ac.uk',
    # Author details
    author='Sam Pepler',
    author_email='sam.pepler@stfc.ac.uk',
    # Choose your license
    license='BSD',
    install_requires=['tabulate', 'click', 'elasticsearch'],

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Beta',
        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='ingest',
    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(),

    entry_points={
        'console_scripts': [
            'catalogue_coverage=cat_complete.completeness_finder:main',
        ],
    },
)