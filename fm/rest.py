#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json
import requests

from http import HTTPStatus

from km.fm.log import Log

# ----------------------------------------------------------------------------------------------------------------------

REST_RETRIES = 3

class Rest():

    @staticmethod
    def _rest_function(f, url, headers=None, data=None):

        r = None
        retries = 0
        status = HTTPStatus.REQUEST_TIMEOUT
        while (retries < REST_RETRIES) and (status == HTTPStatus.REQUEST_TIMEOUT):
            retries += 1

            try:
                r = f(url, headers=headers, data=data)
            except requests.exceptions.Timeout as e:
                status = HTTPStatus.REQUEST_TIMEOUT
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code
            except requests.exceptions.ConnectionError as e:
                status = HTTPStatus.SERVICE_UNAVAILABLE
            except requests.exceptions.RequestException as e:
                status = e.response.status_code
            except:
                status = HTTPStatus.BAD_REQUEST
            else:
                status = r.status_code

        reply = r.text if (status//100) == 2 else None
        return status, reply


    @staticmethod
    def get(node, attribute):

        #
        # Send the REST command to the server.
        #
        headers = { "Accept": "application/json", "Content-Type": "application/json" }
        url = 'http://{address}{attribute}'.format(address=node.address, attribute=attribute)

        status, reply = Rest._rest_function(requests.get, url, headers=headers)

        if status != 200:
            Log.error('Rest(GET): {} failed with status {}', url,status)
            return False, None

        #
        # Good reply - need to convert from string -> data
        #
        if reply.startswith('<pre>') : reply = reply[5:]
        if reply.endswith('</pre>')  : reply = reply[:-6]

        try:
            status,data = True,json.loads(reply)
        except:
            Log.error('Rest.get() : invalid JSON returned.')
            Log.error('Data={}', reply)
            status,data = False,None

        return status, data


    @staticmethod
    def patch(node, attribute, value):

        #
        # Convert the input to JSON format.
        #
        try:
            data = json.dumps(value)
        except:
            Log.error('Rest.(PATCH) : could not convert input to JSON.')
            Log.error('Input={}', value)
            return False,None

        #
        # Send the REST command to the server.
        #
        headers = { "Accept": "application/json", "Content-Type": "application/json" }
        url = 'http://{address}{attribute}'.format(address=node.address, attribute=attribute)

        status, _ = Rest._rest_function(requests.patch, url, headers=headers, data=data)

        if status != 204:
            Log.error('Rest(PATCH): {} failed with status {}', url,status)

        return status == 204, None

# ----------------------------------------------------------------------------------------------------------------------

