#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json

from km.fm.log import Log

# ----------------------------------------------------------------------------------------------------------------------

class Chassis():

    def __init__(self, node, name):
        self.node = node
        self.name = name
        self.configuration = node.configuration[name]


    def ready(self):
        status, attr = self.node.get(self.name)
        if status:
            return attr['PowerState'] == 'On' and attr['Status']['State'] == 'Enabled' and attr['Status']['Health'] == 'OK'
        else:
            return False

# ----------------------------------------------------------------------------------------------------------------------
