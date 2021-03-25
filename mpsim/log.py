#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import json
import socket

from resolve import resolve

# ----------------------------------------------------------------------------------------------------------------------

class Log():
    socket = None
    address = None
    node_name = None

    @staticmethod
    def Init(parameters):

        Log.node_name = parameters['NODENAME']
        Log.address = (resolve(parameters['LOGGER'])[0], 8083)

        #
        # Open the socket to the logging endpoint
        #
        Log.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @staticmethod
    def log(level, msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        print('{:<10} : {:<}'.format(level, msg))

        data = { 'src' : Log.node_name, 'level' : level, 'msg' : msg }
        packet = json.dumps(data).encode('utf-8')
        Log.socket.sendto(packet, Log.address)

# ----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def debug(msg, *args, **kwargs):
        Log.log('debug', msg, *args, **kwargs)

    @staticmethod
    def info(msg, *args, **kwargs):
        Log.log('info', msg, *args, **kwargs)

    @staticmethod
    def warning(msg, *args, **kwargs):
        Log.log('warning', msg, *args, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        Log.log('error', msg, *args, **kwargs)

    @staticmethod
    def critical(msg, *args, **kwargs):
        Log.log('critical', msg, *args, **kwargs)

# ----------------------------------------------------------------------------------------------------------------------

