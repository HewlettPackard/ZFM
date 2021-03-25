#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json
import glob
import copy
import socket

from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

from km.sim.switch      import Switch
from km.sim.compute     import Compute
from km.sim.io          import IO
from km.sim.memory      import Memory

# ----------------------------------------------------------------------------------------------------------------------

def browser_update(node):
    def is_redfish(value): return type(value) is str and value.startswith('/redfish/v1')
    def href(value): return '<a href={0}>{0}</a>'.format(value)

    if type(node) is list:
        for i,value in enumerate(node):
            if is_redfish(value): node[i] = href(value)
            browser_update(node[i])
    elif type(node) is dict:
        for key,value in node.items():
            if is_redfish(value): node[key] = href(value)
            browser_update(value)

# ----------------------------------------------------------------------------------------------------------------------

#
# Method    Scope           Semantics
# -------   ----------      ----------------------------------------------------
# GET       collection      Retrieve all resources in a collection
# GET       resource        Retrieve a single resource
# HEAD      collection      Retrieve all resources in a collection (header only)
# HEAD      resource        Retrieve a single resource (header only)
# POST      collection      Create a new resource in a collection
# PUT       resource        Update a resource
# PATCH     resource        Update a resource
# DELETE    resource        Delete a resource
# OPTIONS   any             Return available HTTP methods and other options
#

# ----------------------------------------------------------------------------------------------------------------------

class RestHandler(BaseHTTPRequestHandler):

    def normalize_path(self, path):
        new_path = path

        #
        # Prepend '/' if needed.
        # If the file name doesn't begin with '/redfish/v1', then add it.
        # If the file name ends with 'index.json', remove it.
        # Strip off the trailing '/'.
        #
        if new_path == '/':
            new_path = self.server.redfish_base
        if new_path[0] != '/':
            new_path = '/{}'.format(new_path)
        if not new_path.startswith(self.server.redfish_base):
            new_path = '{}/{}'.format(self.server.redfish_base, new_path)
        if new_path[-1] == '/':
            new_path = new_path[:-1]
        if new_path.endswith('/index.json'):
            new_path = new_path.rsplit('/',1)[0]
        return new_path

    def log_message(self, format, *args):
        return

    # ----------------------------------------------------------------------------------------------

    def reply(self, status, headers=None, data=None):
        encoded_data = data.encode() if data else None

        if headers and 'Content-Length' not in headers:
            headers['Content-Length'] = str(len(encoded_data))

        try:
            self.send_response(status)
            if headers:
                for key,value in headers.items():
                    self.send_header(key, value)
            self.end_headers()

            if encoded_data:
                self.wfile.write(encoded_data)
        except:
            print('can\'t reply to requester')

    # ----------------------------------------------------------------------------------------------

    def do_HEAD(self):
        print('HEAD {}:{}'.format(self.server.node_address, self.path))
        self.reply(404)

    # ----------------------------------------------------------------------------------------------

    def do_GET(self):
        print('GET {}:{}'.format(self.server.node_address, self.path))
        path = self.normalize_path(self.path)

        #
        # If we don't know this resource, send 404.
        #
        if path not in self.server.cache:
            self.reply(404)
            return

        #
        # Get the resource.  Update the links if requested.
        #
        data = copy.deepcopy(self.server.cache[path])
        if self.server.browser:
            browser_update(data)
            data = '<pre>' + json.dumps(data, indent=4, separators=(',', ': ')) + '</pre>'
            content_type = 'text/html'
        else:
            data = json.dumps(data, indent=4, separators=(',', ': '))
            content_type = 'application/json'

        headers = { 'Content-Type'  : content_type,
                    'Cache-Control' : 'no-cache, no-store, must-revalidate',
                    'Pragma'        : 'no-cache',
                    'Expires'       : '0' }

        self.reply(200, headers, data)

    # ----------------------------------------------------------------------------------------------

    def do_POST(self):
        print('POST {}:{}'.format(self.server.node_address, self.path))

        path = self.normalize_path(self.path)

        data_length = int(self.headers['Content-Length'])

        try:
            data = json.loads(self.rfile.read(data_length).decode('utf-8'))
        except Exception as e:
            print('invalid POST request - JSON improperly formatted')
            self.reply(400)
            return

        #
        # If the resource doesn't exist, then 404.
        # If the resource isn't a collection, then 405.
        # Otherwise, 204
        #
        if path not in self.server.cache:
            self.reply(404)
        elif 'Members' not in self.server.cache[path]:
            self.reply(405)
        else:
            #
            # Find a resource id for the new entry.
            #
            resource = self.server.cache[path]
            members = resource['Members']
            members_id = sorted([ int(x.get('@odata.id').rsplit('/',1)[1]) for x in members ])

            last = members_id[0]
            for x in members_id[1:]:
                if x != last+1: break
                last = x

            #
            # Name the new entry.
            #
            new_id = last + 1
            data_id = '{}/{}'.format(path, new_id)
            data['@odata.id'] = data_id

            #
            # Update the resource to include the new entry.
            #
            resource['Members'].append({'@odata.id' : data_id })
            resource['Members@odata.count'] += 1

            #
            # Put the new entry into the tree.
            #
            self.server.cache[data_id] = data

            #
            # Reply to the user.
            #
            headers = { 'Location' : data_id }
            self.reply(204, headers)

    # ----------------------------------------------------------------------------------------------

    def do_PUT(self):
        print('PUT {}:{}'.format(self.server.node_address, self.path))

        #
        # We don't support this function.
        #
        self.reply(405)

    # ----------------------------------------------------------------------------------------------

    def do_PATCH(self):
        print('PATCH {}:{}'.format(self.server.node_address, self.path))

        path = self.normalize_path(self.path)

        data_length = int(self.headers['Content-Length'])

        try:
            data = json.loads(self.rfile.read(data_length).decode('utf-8'))
        except Exception as e:
            print('invalid PATCH request - JSON improperly formatted')
            self.reply(400)
            return

        #
        # If the resource doesn't exist, then 404.
        # If the resource is a collection, then 405.
        # Otherwise, 204.
        #
        if path not in self.server.cache:
            status = 404
        elif 'Members' in self.server.cache[path]:
            status = 405
        else:
            status = 204
            self.server.node.do_PATCH(path, data)

        #
        # Reply to the user.
        #
        self.reply(status)

    # ----------------------------------------------------------------------------------------------

    def do_DEEPPATCH(self):
        print('DEEPPATCH {}:{}'.format(self.server.node_address, self.path))
        self.reply(405)

    # ----------------------------------------------------------------------------------------------

    def do_DELETE(self):
        print('DELETE {}:{}'.format(self.server.node_address, self.path))

        path = self.normalize_path(self.path)
        parent_path = path.rsplit('/', 1)[0]

        #
        # If the resource doesn't exist, then 404.
        # If the parent doesn't exist, then 405.
        # If the parent isn't a collection, then 405.
        # Otherwise, 204
        #
        if path not in self.server.cache:
            status = 404
        elif parent_path not in self.server.cache:
            status = 405
        elif 'Members' not in self.server.cache[parent_path]:
            status = 405
        else:
            status = 204

            del self.server.cache[path]
            for i,m in enumerate(self.server.cache[parent_path]['Members']):
                if m['@odata.id'] == self.path:
                    del self.server.cache[parent_path]['Members'][i]
                    self.server.cache[parent_path]['Members@odata.count'] -= 1
                    break

        #
        # Reply to the user.
        #
        self.reply(status)

# ----------------------------------------------------------------------------------------------------------------------

class NodeMP():
    def __init__(self, profile):
        if type(profile) is not dict:
            print('can\'t start nodeMP')
            return

        #
        # Resolve the hostname.
        #
        hostname, delimiter, hostport = profile['address'].partition(':')
        if not hostport: hostport = '8081'

        try:
            hostaddr = socket.gethostbyname(hostname)
        except:
            print('can\'t resolve the server address {}'.format(profile['address']))
            sys.exit(0)

        #
        # Setup the server environment.
        #
        self.address = hostaddr
        self.port = int(hostport)

        profile['address'] = hostaddr + ':' + hostport
        self.profile = profile

        self.server = HTTPServer((self.address, self.port), RestHandler)
        self.server.node_name = profile['name']
        self.server.node_type = profile['type']
        self.server.node_address = profile['address']
        self.server.node_port = self.port
        self.server.redfish_base = '/redfish/v1'
        self.server.browser = profile['browser']
        self.server.profile = profile

        #
        # Read the attributes.
        #
        attribute_filename = profile['attributes']
        try:
            with open(attribute_filename) as f:
                self.server.cache = json.load(f)
        except:
            print('can\'t read attribute file', attribute_filename)
            sys.exit(0)

        #
        # Create the GenZ environment.
        #
        if   self.server.node_type == 'Memory'  : self.server.node = Memory(self.server)
        elif self.server.node_type == 'Switch'  : self.server.node = Switch(self.server)
        elif self.server.node_type == 'Compute' : self.server.node = Compute(self.server)
        elif self.server.node_type == 'IO'      : self.server.node = IO(self.server)


    def run(self):
        print('starting {} @ {}:{}'.format(self.server.node_name, self.address, self.port))
        self.server.serve_forever()

# ----------------------------------------------------------------------------------------------------------------------
