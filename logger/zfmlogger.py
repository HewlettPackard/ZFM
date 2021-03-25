#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import json
import time
import socket
import argparse

from km.logger.log import Log

# ----------------------------------------------------------------------------------------------------------------------

def log(packet):
    src   = packet.get('src', 'unknown')
    level = packet.get('level', 'info')
    msg   = packet.get('msg', '***** missing msg *****')

    Log.log(level, src, msg)

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    #
    # Start the syslog/console logging.
    #
    Log.Init('debug')

    parser = argparse.ArgumentParser(description='Gen-Z logger')
    parser.add_argument('-H', '--host',  help='server address',   required=False,  default=socket.gethostname())
    args = vars(parser.parse_args())

    #
    # Get the IP address for the endpoint
    #
    ip_address = socket.gethostbyname(args['host'])

    #
    # Open the logging socket.
    #
    log_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    log_socket.bind((ip_address, 8083))

    #
    # Main loop.
    #
    while True:
        message, address = log_socket.recvfrom(65536)
        packet = json.loads(message.decode('utf-8'))
        log(packet)

    while True:
        try:
            message, address = log_socket.recvfrom(65536)
            packet = json.loads(message.decode('utf-8'))
            log(packet)
        except KeyboardInterrupt:
            print('user interrupt caught - exiting')
            sys.exit(1)
        except:
            print('Unexpected error:', sys.exc_info()[0])

# ----------------------------------------------------------------------------------------------------------------------

