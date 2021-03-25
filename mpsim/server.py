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
import importlib

from log import Log
from threading import Thread
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

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
            new_path = self.server.env['redfish_base']
        if new_path[0] != '/':
            new_path = '/{}'.format(new_path)
        if not new_path.startswith(self.server.env['redfish_base']):
            new_path = '{}/{}'.format(self.server.env['redfish_base'], new_path)
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
            Log.info('can\'t reply to requester')

    # ----------------------------------------------------------------------------------------------

    def do_HEAD(self):
        Log.info('HEAD {}', self.path)

    # ----------------------------------------------------------------------------------------------

    def do_GET(self):
        Log.info('GET {}', self.path)
        path = self.normalize_path(self.path)

        #
        # If we don't know this resource, send 404.
        #
        if path not in self.server.attributes:
            self.reply(404)
            return

        #
        # Get the resource.  Update the links if requested.
        #
        data = copy.deepcopy(self.server.attributes[path])
        if self.server.env['browser']:
            browser_update(data)
            data = '<pre>' + json.dumps(data, indent=4, separators=(',', ': ')) + '</pre>'
            content_type = 'text/html'
        else:
            data = json.dumps(data, indent=4, separators=(',', ': '))
            content_type = 'application/json'

        headers = { 'Content-Type'   : content_type,
                    'Cache-Control'  : 'no-cache, no-store, must-revalidate',
                    'Pragma'         : 'no-cache',
                    'Expires'        : '0' }

        self.reply(200, headers, data)

    # ----------------------------------------------------------------------------------------------

    def do_POST(self):
        Log.info('POST {}', self.path)

        path = self.normalize_path(self.path)

        data_length = int(self.headers['Content-Length'])

        try:
            data = json.loads(self.rfile.read(data_length).decode('utf-8'))
        except Exception as e:
            Log.info('invalid POST request - JSON improperly formatted')
            self.reply(400)
            return

        #
        # If the resource doesn't exist, then 404.
        # If the resource isn't a collection, then 405.
        # Otherwise, 204
        #
        if path not in self.server.attributes:
            self.reply(404)
        elif 'Members' not in self.server.attributes[path]:
            self.reply(405)
        else:
            #
            # Find a resource id for the new entry.
            #
            resource = self.server.attributes[path]
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
            self.server.attributes[data_id] = data

            #
            # Reply to the user.
            #
            headers = { 'Location' : data_id }
            self.reply(204, headers)

    # ----------------------------------------------------------------------------------------------

    def do_PUT(self):
        Log.info('PUT {}', self.path)
        self.reply(405)

    # ----------------------------------------------------------------------------------------------

    def do_PATCH(self):
        Log.info('PATCH {}', self.path)

        path = self.normalize_path(self.path)

        data_length = int(self.headers['Content-Length'])

        try:
            data = json.loads(self.rfile.read(data_length).decode('utf-8'))
        except Exception as e:
            Log.info('invalid PATCH request - JSON improperly formatted {} -> {}', data_length, data)
            self.reply(400)
            return

        #
        # If the resource doesn't exist, then 404.
        # If the resource is a collection, then 405.
        # Otherwise, 204.
        #
        if path not in self.server.attributes:
            status = 404
        elif 'Members' in self.server.attributes[path]:
            status = 405
        else:
            status = 204
            self.server.node.do_PATCH(path, data)

        #
        # Reply to user.
        #
        self.reply(status)

    # ----------------------------------------------------------------------------------------------

    def do_DEEPPATCH(self):
        Log.info('DEEPPATCH {}', self.path)
        self.reply(405)

    # ----------------------------------------------------------------------------------------------

    def do_DELETE(self):
        Log.info('DELETE {}', self.path)

        path = self.normalize_path(self.path)
        parent_path = path.rsplit('/', 1)[0]

        #
        # If the resource doesn't exist, then 404.
        # If the parent doesn't exist, then 405.
        # If the parent isn't a collection, then 405.
        # Otherwise, 204
        #
        if path not in self.server.attributes:
            status = 404
        elif parent_path not in self.server.attributes:
            status = 405
        elif 'Members' not in self.server.attributes[parent_path]:
            status = 405
        else:
            status = 204

            del self.server.attributes[path]
            for i,m in enumerate(self.server.attributes[parent_path]['Members']):
                if m['@odata.id'] == self.path:
                    del self.server.attributes[parent_path]['Members'][i]
                    self.server.attributes[parent_path]['Members@odata.count'] -= 1
                    break

        #
        # Reply to user.
        #
        self.reply(status)

# ----------------------------------------------------------------------------------------------------------------------

class RedfishServer():
    def __init__(self, node):
        #
        # Setup the REDfish server.
        #
        addr,_,port = node.env['profile']['address'].partition(':')
        if not port: port = '8081'

        self.server = HTTPServer((addr, int(port)), RestHandler)
        self.server.node = node
        self.server.env = node.env
        self.server.attributes = node.env['attributes']

        #
        # Create the REDfish thread.
        #
        self.thread = Thread(target=self.run, daemon=True)


    def run(self):
        self.server.serve_forever()


    def start(self):
        self.thread.start()

# ----------------------------------------------------------------------------------------------------------------------
