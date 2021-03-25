#!/usr/bin/env python3

#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

from setuptools import setup

setup(
    name='km',
    package_dir = { 'km.fm'        : './fm',
                    'km.sim'       : './sim',
                    'km.conf'      : './conf',
                    'km.arch'      : './arch',
                    'km.route'     : './route',
                    'km.logger'    : './logger',
                    'km.routers'   : './routers',
                    'km.templates' : './templates',
                  },

    url='https://somewhere.com',
    author='First Last',
    author_email='xxx@yyy.com',
    packages=[ 'km.fm', 'km.sim', 'km.templates', 'km.conf', 'km.arch', 'km.route', 'km.logger', 'km.routers' ],
    install_requires=['requests'],
    version='0.1',
    license='MIT',
    description='ZFM tools',
    scripts=['fm/zfm.py', 'sim/zfmsim.py', 'conf/zfmconf.py', 'route/zfmroute.py',
             'misc/zfmcurl.py', 'misc/zfminfo.py', 'misc/zfmlink.py', 'misc/zfmperf.py',
             'misc/zfmport.py', 'misc/zfmrest.py', 'misc/zfmtr.py', 'logger/zfmlogger.py',
             'tools/vmctl.py' ]
)


