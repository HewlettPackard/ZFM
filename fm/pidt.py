#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json

# ----------------------------------------------------------------------------------------------------------------------

class PIDT():

    def __init__(self, node, name):
        self.node = node
        self.name = name
        self.table = node.configuration[name]['Gen-Z']['PIDT']


    def get(self):
        status,attr = self.node.get(self.name)
        return status,attr['Gen-Z']['PIDT']


    def patch(self):
        status,_ = self.node.patch(self.name, { 'Gen-Z' : { 'PIDT' : self.table }})
        return status

# ----------------------------------------------------------------------------------------------------------------------
