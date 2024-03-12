# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in glistercp_hotel/__init__.py
from glistercp_hotel import __version__ as version

setup(
	name='glistercp_hotel',
	version=version,
	description='Hotel Management App for ERPNext',
	author='Glistercp',
	author_email='support@glistercp.com.ng',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
