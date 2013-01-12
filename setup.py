#!/usr/bin/python

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

from textyserver import __version__

setup(name = "textyserver",
		version = __version__,
		description = "TextyServer",
		long_description="",
		author = "Texty Team",
		author_email = "mansam@csh.rit.edu",
		url = "www.example.org",
		packages = find_packages(exclude=['ez_setup', 'example']),
		include_package_data = True,
		package_data = {
			'': ['*.yaml', 'conf/*.yaml', 'installer/*', 'filters/**/*', 'filters/*.xsl'],
		},
		license = '',
		scripts = [],
		platforms = 'Posix; MacOS X; Windows',
		classifiers = [ 
			'Development Status :: 3 - Alpha',
			'Intended Audience :: Developers',
			'Operating System :: OS Independent',
			'Topic :: Internet',
		],
		install_requires = [
			"pyyaml",
			"webob==1.1",
			"boto",
			"botoweb",
			"lxml",
			"pytz",
		],
	)
