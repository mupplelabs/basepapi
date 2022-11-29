#!/usr/bin/env python
# BasePAPI Class for simple OneFS Platform API interaction
#
# Copyright C 2002-2022 by DELL Technologies. All rights are reserved.
# Isilon and Isilon Systems are registered trademarks of Dell Technologies.
#
# To be used to simplify papi access from remote, without the need of a full SDK.
# 
# Requires: requests library
# get requests: pip install requests
# 
# Example Usage: 
# 
# from papi import basepapi
# papi = basepapi('ClusterIP', 'Username', 'Password') 
# response = papi.get('/1/cluster/identity')
# print(response.body)
#
# Output:
# {u'logon': {u'motd_header': u'', u'motd': u''}, u'description': u'', u'name': u'joshuatree'}
#
# Supports: GET, HEAD, PUT, POST and DELETE operations against PlatformAPI Endpoints.
# Leverages Session Authentication, hence best practice is to point it to a given Nodes IP Adress rather than a SmartConnect FQDN.
#
# Returns a PapiResponse Class, containing: Status Code, response headers, and JSON Body as dict. 
#
# More info see README.md

import requests
import json
from requests import exceptions

from requests.sessions import session

class basepapi:
    class PapiResponse :
        def __init__(self, rObject) :
            if isinstance(rObject, requests.models.Response) :
                # private Respone Object Building Function
                    self.status = rObject.status_code
                    self.headers = rObject.headers
                    try :                                   # validate the response body is a JSON      
                        self.body = rObject.json()
                    except :
                        self.body = rObject.text         # not a JSON return the "text" as is
            else :
                raise TypeError("Input data of wrong type!")

    class papiException(Exception) :
        pass

    class papiConnectionError(papiException) :
        def __init__(self, rObject) :
            if isinstance(rObject, requests.models.ConnectionError) :
                    self.status = rObject
                    self.text = str(rObject)
            else :
                raise TypeError("Unhandled connection error condition occured!")

    class papiError(papiException) :
        def __init__(self, rObject) :
            if isinstance(rObject, requests.models.HTTPError) :
                    if isinstance(rObject.response.status_code, int) :
                        self.status = rObject.response.status_code
                    else :
                        self.status = rObject
                    self.text = str(rObject)
            else :
                raise TypeError("Unhandled HTTP Error condition occured!")

    def __init__(self, HOST, username, password, port=8080, timeout=15, secure=False, papiService = 'platform', papiAgent = "OneFS PlatformAPI Client for Python"):
        # Data needed for Session Authentication:
        self.__auth = {
            'username': username,
            'password': password,
            'services': [papiService] # valid options: ['platform', 'namespace']
        }

        # default urls and prefixes
        self.__sessionURL = '/session/1/session'
        self.__timeout = timeout # connection timeout in seconds
        self.papiService = '/' + papiService # API Service of this session...
        
        #Session Status variables
        self.connected = False
        self.services = [] # store list of services for current session

        # General Wrappers 
        self.HOST = HOST
        self.port = port
        self.url = 'https://' + self.HOST + ':' + str(self.port)

        #Prepare and create HTTPS Requests session object
        self.__session = requests.Session()
        self.__session.headers.update({'content-type': 'application/json', 'User-Agent': papiAgent})
        self.__session.verify = secure
     
        # disable warnings on non secure certificates if ssl verification is turned off
        if(not secure):
            requests.packages.urllib3.disable_warnings()

    # the public session connect, disconnect and Status Update functions go here:

    def connect(self) : # Connect to PAPI and request an Auth Session Cookie
        try:
            response = self.__session.post(self.url + self.__sessionURL, data=json.dumps(self.__auth), timeout=self.__timeout)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise self.papiConnectionError(e)
        except requests.exceptions.HTTPError as e :
            raise self.papiError(e)
        else :
            nHeader = { # add headers needed for CSRF support, without these we cannot use the session cookie for anything papi
                    'Origin': self.url,
                    'X-CSRF-Token': response.cookies.get('isicsrf')
            }
            self.__session.headers.update(nHeader)
            self.services = response.json()['services'] # load authorized services
            self.connected = True # set connection state
            myStatus = self.PapiResponse(response)
            return myStatus

    def disconnect(self) : # in case we need a disconnect funtion... here we can disconnect from a Session
        try:
            response = self.__session.delete(self.url + self.__sessionURL)
        except requests.exceptions.ConnectionError as e:
            raise self.papiConnectionError(e)
        except requests.exceptions.HTTPError as e :
            raise self.papiError(e)
        else :
            self.connected = False
            myStatus = self.PapiResponse(response)
            return myStatus

    def getStatus(self) : # get the current Sessions Status
        try:
            response = self.__session.get(self.url + self.__sessionURL)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise self.papiConnectionError(e)
        except requests.exceptions.HTTPError as e :
            self.connected = False
            raise self.papiError(e)
        else :
            myStatus = self.PapiResponse(response)
            return myStatus
    
    # the private function that does the actual work...

    def __request(self, method, uri, body={}, args={}, headers={} ) :
        # if not already connected create the session to OneFS
        if(not self.connected): # connect
            self.connect()
        # create and send the request:
        myurl = self.url + self.papiService + uri
        if headers and isinstance(headers, dict) : # Add headers if specified... MUST be a dict!!!
            self.__session.headers.update(headers)
            # shall we validate the header format? and add error handling here?
        try: # Do the request.
            response = self.__session.request(method, url=myurl, params=args, json=body)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            myStatus = self.papiConnectionError(e)
            raise myStatus
        except requests.exceptions.HTTPError as e :
            if self.connected and e.response.status_code == 401 :
                self.connected = False
            myStatus = self.papiError(e)
            raise myStatus
        # clean up the response if successfull call
        output = self.PapiResponse(response)
        output.url = myurl
        output.rheaders = self.__session.headers 
        if headers and isinstance(headers, dict) : # Clean up API Call Specific Headers 
            for key in headers:
                if key in self.__session.headers:
                    del self.__session.headers[key]
        return output # extract body json to dict

    #   define actual methods for PUT, POST, GET, HEAD and DELETE

    def get(self, uri, body=None, args=None, headers={}): 
        pResponse = self.__request('GET', uri, body, args, headers)
        return pResponse

    def put(self, uri, body=None, args=None, headers={}):
        pResponse = self.__request('PUT', uri, body, args, headers)
        return pResponse

    def head(self, uri, body=None, args=None, headers={}):
        pResponse = self.__request('HEAD', uri, body, args, headers)
        return pResponse

    def post(self, uri, body=None, args=None, headers={}):
        pResponse = self.__request('POST', uri, body, args, headers)
        return pResponse

    def delete(self, uri, body=None, args=None, headers={}):
        pResponse = self.__request('DELETE', uri, body, args, headers)
        return pResponse