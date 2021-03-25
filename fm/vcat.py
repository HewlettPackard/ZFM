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

class _VCTable():

    def __init__(self, node, name):
        self.node = node
        self.name = name
        self.configuration = node.configuration[name]


    def get(self):
        status,attr = self.node.get(self.name)
        return status,attr


    def patch(self):
        all_status = True
        for member_id in self.configuration['Members']:
            member_name = member_id['@odata.id']
            member_attr = self.node.configuration[member_name]
            if len(member_attr['VCATEntry']):
                status,_ = self.node.patch(member_name, { 'VCATEntry' : member_attr['VCATEntry'] })
            else:
                status = True
            all_status &= status

        return all_status


# ----------------------------------------------------------------------------------------------------------------------

class VCAT(_VCTable):
    def __init__(self, node, name):
        super().__init__(node, name)


# ----------------------------------------------------------------------------------------------------------------------

class REQ_VCAT(_VCTable):
    def __init__(self, node, name):
        super().__init__(node, name)


# ----------------------------------------------------------------------------------------------------------------------

class RSP_VCAT(_VCTable):
    def __init__(self, node, name):
        super().__init__(node, name);

# ----------------------------------------------------------------------------------------------------------------------
