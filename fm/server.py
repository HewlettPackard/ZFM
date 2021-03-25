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
import datetime
import subprocess

from urllib      import parse
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

from km.fm.log       import Log
from km.fm.formatter import ZFMFormatter

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

class GenZHandler(BaseHTTPRequestHandler):

    def normalize_path(self, path):
        new_path = path

        #
        # Strip off the leading '/'.
        # If the file name doesn't being with 'redfish/v1', then add it.
        # If the file name ends with 'index.json', remove it.
        # Strip off the trailing '/'.
        #
        if new_path.startswith(os.sep):
            new_path = new_path[1:]
        if not new_path.startswith(self.server.redfish_base):
            new_path = os.path.join(self.server.redfish_base, new_path)
        if os.path.basename(new_path) == 'index.json':
            new_path = os.path.dirname(new_path)
        if new_path.endswith(os.sep):
            new_path = new_path[:-1]
        return new_path

    # ----------------------------------------------------------------------------------------------

    def log_message(self, format, *args):
        return

    # ----------------------------------------------------------------------------------------------

    def reply(self, status, headers=None, data=None):
        try:
            self.send_response(status)
            if headers:
                for key,value in headers.items():
                    self.send_header(key, value)
            self.end_headers()

            if data:
                encoded_data = data.encode()
                self.wfile.write(encoded_data)
        except:
            Log.error('can\'t reply to requester')

    # ----------------------------------------------------------------------------------------------

    def do_GET(self):
        if 'favicon.ico' in self.path:
            return 404, None

        Log.info('GET {}:{}', self.server.node_address, self.path)

        parsed_url = parse.urlsplit(self.path)
        tokens = parsed_url.path.split('/')
        query = parsed_url.query
        parameters = parse.parse_qs(query)

        if 'format' not in parameters: parameters['format'] = ['BROWSER']

        #
        # Remove empty strings from the parsed URL.
        #
        while (len(tokens) > 0) and (tokens[0] == ''):
            del tokens[0]

        while (len(tokens) > 0) and (tokens[-1] == ''):
            del tokens[-1]

        if (len(tokens) > 0) and (tokens[-1] == 'favicon.ico'):
            return 404, None

        #
        # Valid requests are:
        #   1) []          -> fabric request
        #   2) [name]      -> node request
        #   3) [name,port] -> port request
        #
        status,data = 404,None

        fabric = self.server.fabric
        node = None
        port = None

        #
        # Validate that the parameters are in range and correct.
        #
        if len(tokens) > 2:
            Log.error('too many fields in URL {}', self.path)
            return 404, None

        if len(tokens) == 2 and not tokens[1].isdigit():
            Log.error('invalid URL (port incorrect) {}', self.path)
            return 404, None

        if len(tokens) >= 1:
            node = self.server.fabric.locate_node(tokens[0])
            if not node:
                Log.error('invalid URL (node incorrect) {}', self.path)
                return 404, None

        if len(tokens) == 2:
            value = int(tokens[1])
            if not (node.profile['portStart'] <= value < node.profile['portEnd']):
                Log.error('invalid URL (port out of range) {}', self.path)
                return 404, None
            port = node.ports[value]

        #
        # Execute the command at the appropriate level.
        #
        if len(tokens) == 0:
            status, data = fabric.GET(parameters)
        elif len(tokens) == 1:
            status, data = node.GET(parameters)
        elif len(tokens) == 2:
            status, data = port.GET(parameters)

        if status == 200:
            data['ZFM'] = self.server.node_address
            output = self.server.formatter.format(data, parameters['format'][0])

        #
        # Send the reply back to the requester.
        #
        headers = {'Content-type'  :  'text/html',
                   'Cache-Control' :  'no-cache, no-store, must-revalidate',
                   'Pragma'        :  'no-cache',
                   'Expires'       :  '0' }

        payload = output if status == 200 else None

        self.reply(status, headers, payload)

    # ----------------------------------------------------------------------------------------------

    def do_POST(self):
        Log.info('POST {}:{}', self.server.node_address, self.path)

        path = self.normalize_path(self.path)

        data_length = int(self.headers["content-length"])
        data = json.loads(self.rfile.read(data_length).decode("utf-8"))
        data_id = data['@odata.id']

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
            members_id = sorted([ int(x.get('@odata.id').rsplit(os.sep,1)[1]) for x in members ])

            last = members_id[0]
            for x in members_id[1:]:
                if x != last+1: break
                last = x

            #
            # Name the new entry.
            #
            new_id = last + 1
            data_id = data_id.rsplit(os.sep, 1)[0]
            data_id = os.path.join(data_id, str(new_id))
            data['@odata.id'] = data_id

            #
            # Update the resource to include the new entry.
            #
            resource['Members'].append({'@odata.id' : data_id })
            resource['Members@odata.count'] += 1

            #
            # Put the new entry into the tree.  (The resource name doesn't have a leading '/'.)
            #
            new_id = data_id
            if new_id[0] == os.sep: new_id = new_id[1:]
            self.server.cache[new_id] = data

            #
            # Reply to the user.
            #
            headers = { "Location" : data_id, "Content-Length" : "0" }
            self.reply(204, headers)

    # ----------------------------------------------------------------------------------------------

    def do_PUT(self):
        Log.info('PUT {}:{}', self.server.node_address, self.path)

        #
        # We don't support this function.
        #
        self.reply(405)

    # ----------------------------------------------------------------------------------------------

    def do_PATCH(self):
        Log.info('PATCH {}:{}', self.server.node_address, self.path)

        path = self.normalize_path(self.path)

        data_length = int(self.headers["content-length"])
        data = json.loads(self.rfile.read(data_length).decode("utf-8"))
        data_id = data['@odata.id']

        #
        # If the resource doesn't exist, then 404.
        # If the resource is a collection, then 405.
        # Otherwise, 204.
        #
        if path not in self.server.cache:
            self.reply(404)
        elif 'Members' in self.server.cache[path]:
            self.reply(405)
        else:
            #
            # Update the resource.
            #
            update_resource(self.server.cache[path], data)

            #
            # Reply to the user.
            #
            headers = { "Location" : data_id, "Content-Length" : "0" }
            self.reply(204, headers)

    # ----------------------------------------------------------------------------------------------

    def do_DELETE(self):
        Log.info('DELETE {}:{}', self.server.node_address, self.path)

        path = self.normalize_path(self.path)
        parent_path = path.rsplit(os.sep, 1)[0]

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

        self.reply(status)

# ----------------------------------------------------------------------------------------------------------------------

class Server():
    def __init__(self, hostname, fabric):

        #
        # Resolve the hostname.
        #
        hostname, delimiter, hostport = hostname.partition(':')
        if not hostport: hostport = '60000'

        try:
            hostname = socket.gethostbyname(hostname)
        except:
            Log.error('can\'t resolve the ZFM server address {}', hostname)
            sys.exit(0)

        #
        # Setup the server environment.
        #
        self.address = hostname
        self.port = int(hostport)
        self.server = None

        try:
            self.server = HTTPServer((self.address, self.port), GenZHandler)
        except:
            output = subprocess.check_output('lsof -i:{}'.format(self.port), shell=True)
            Log.error('can\'t create HTTP server')
            Log.error(output.decode('utf-8'))
            sys.exit(0)

        self.server.formatter = ZFMFormatter()
        self.server.node_address = hostname
        self.server.redfish_base = os.path.join('redfish', 'v1')
        self.server.fabric = fabric


    def run(self):
        Log.info('starting ZFM server @ {}:{}', self.address, self.port)
        self.server.serve_forever()

# ----------------------------------------------------------------------------------------------------------------------
