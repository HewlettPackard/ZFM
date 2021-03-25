#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json
import logging
import logging.handlers

# ----------------------------------------------------------------------------------------------------------------------

class Log():

    log_level_funcs = {}

    log_level_map = { 'debug'    : logging.DEBUG,
                      'info'     : logging.INFO,
                      'warning'  : logging.WARNING,
                      'error'    : logging.ERROR,
                      'critical' : logging.CRITICAL }

    log_level = log_level_map['warning']
    logger = None


    @staticmethod
    def Init(level):
        if level in Log.log_level_map:
            Log.log_level = Log.log_level_map[level]

        syslog_file = '/dev/log' if sys.platform.lower() == 'linux' else '/var/run/syslog'

        #
        # Formatter.
        #
        formatter = logging.Formatter('{name} {levelname:8s} : {message}', style='{')

        #
        # Syslog handler.
        #
        syslog_handler = logging.handlers.SysLogHandler(address=syslog_file, facility='local1')
        syslog_handler.setLevel(Log.log_level)
        syslog_handler.setFormatter(formatter)

        #
        # Console handler.
        #
        console_handler = logging.StreamHandler()
        console_handler.setLevel(Log.log_level)
        console_handler.setFormatter(formatter)

        #
        # Create logger and add the handlers.
        #
        Log.logger = logging.getLogger('ZFM')
        Log.logger.setLevel(Log.log_level)
        Log.logger.addHandler(syslog_handler)
        Log.logger.addHandler(console_handler)

        #
        # Setup the level -> function map.
        #
        Log.log_level_funcs['debug']     = Log.logger.debug
        Log.log_level_funcs['info']      = Log.logger.info
        Log.log_level_funcs['warning']   = Log.logger.warning
        Log.log_level_funcs['error']     = Log.logger.error
        Log.log_level_funcs['critical']  = Log.logger.critical

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def log(level, src, msg):
        if level not in Log.log_level_map:
            level = 'info'

        Log.log_level_funcs[level]('{:<15} : {:<}'.format(src, msg))

# ----------------------------------------------------------------------------------------------------------------------

