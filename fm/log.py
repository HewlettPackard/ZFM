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

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def debug(msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        Log.logger.debug(msg)

    @staticmethod
    def info(msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        Log.logger.info(msg)

    @staticmethod
    def warning(msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        Log.logger.warning(msg)

    @staticmethod
    def error(msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        Log.logger.error(msg)

    @staticmethod
    def critical(msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        Log.logger.critical(msg)

# ----------------------------------------------------------------------------------------------------------------------

