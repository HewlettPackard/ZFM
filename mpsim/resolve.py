#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import os
import sys
import json
import glob
import time
import socket
import argparse

node = None
parameters = {}

# ----------------------------------------------------------------------------------------------------------------------

def resolve(address, default_port=8081):
    hostname, delimiter, hostport = address.partition(':')
    hostaddr = socket.gethostbyname(hostname)
    hostport = default_port if not hostport else int(hostport)

    return hostaddr, hostport

# ----------------------------------------------------------------------------------------------------------------------
