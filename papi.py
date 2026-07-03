#!/usr/bin/env python
"""
BasePAPI - A simple OneFS Platform API interaction library.

This module provides a lightweight interface for interacting with Dell PowerScale/Isilon
clusters via the Platform API (PAPI), without requiring a full SDK installation.

Requirements:
    - requests library (install via: pip install requests)

Example Usage:
    from papi import basepapi
    
    papi = basepapi('ClusterIP', 'Username', 'Password')
    response = papi.get('/1/cluster/identity')
    print(response.body)
    
    # Output:
    # {'logon': {'motd_header': '', 'motd': ''}, 'description': '', 'name': 'joshuatree'}

Supported Operations:
    GET, HEAD, PUT, POST, and DELETE against Platform API endpoints.

Notes:
    - Uses session-based authentication for efficiency
    - Returns PapiResponse objects containing: status code, headers, and JSON body as dict

For more information, see README.md
"""

import requests
import json
import http.client
import urllib.error

class PapiResponse(object):
    """
    Container for OneFS Platform API responses.
    
    Stores the HTTP response data from PAPI calls including status code,
    headers, response body, and the request URI.
    
    Attributes:
        status (int): HTTP status code of the response.
        headers (dict): HTTP response headers.
        body (dict): JSON response body parsed as a dictionary.
        uri (str): The URI that was requested.
    """

    __slots__ = ("status", "headers", "body", "uri")

    def __init__(self, status=None, headers=None, body=None, uri=None):
        self.status = status
        self.headers = headers
        self.body = body
        self.uri = uri

    def __str__(self):
        return "Status: {status}, Headers: {headers}, Body: {body}, URI: {uri}".format(
            status=self.status,
            headers=self.headers,
            body=self.body,
            uri=self.uri,
        )

    def __repr__(self):
        return "PapiResponse(status={!r}, headers={!r}, body={!r}, uri={!r})".format(
            self.status, self.headers, self.body, self.uri
        )

    def raise_for_status(self):
        """
        Raise a PapiError if the response status code indicates an error.
        
        Checks if the HTTP status code is outside the successful 2XX range
        and raises a PapiError exception if so. This method provides symmetry
        with requests.Response.raise_for_status() for consistent error handling.
        
        Raises:
            PapiError: If the status code is not in the 2XX range (200-299).
        """
        if not (http.client.OK <= self.status < http.client.MULTIPLE_CHOICES):
            raise PapiError(self.uri, self.status, self.body, self.headers)

class PapiError(urllib.error.URLError):
    """
    Exception raised when a PAPI request returns an error status code.
    
    This exception is raised by PapiResponse.raise_for_status() when the HTTP
    status code indicates an error (not in the 2XX range).
    
    Attributes:
        uri (str): The URI that was requested.
        status (int): HTTP status code of the response.
        body (dict): JSON response body parsed as a dictionary.
        headers (dict): HTTP response headers.
    """
    def __init__(self, uri, status, body, headers):
        self.uri = uri
        self.status = status
        self.body = body
        self.headers = headers

    def __repr__(self):
        return "PapiError(uri={!r}, code={!r}, body={!r}, headers={!r})".format(
            self.uri, self.status, self.body, self.headers
        )

    def __str__(self):
        return "PapiError: {} returned {}\nBody: {}\nHeaders: {}".format(
            self.uri,
            self.status,
            self.body,
            self.headers,
        )

    # HTTPError alias to ease with cross-functional compatibility.
    @property
    def code(self):
        return self.status

class basepapi:
    """
    A class for interacting with the OneFS Platform API (PAPI).
    
    Provides methods for authenticating and making REST API calls (GET, HEAD, PUT, POST, DELETE)
    to Dell PowerScale/Isilon clusters using session-based authentication.
    
    Attributes:
        HOST (str): The IP address or hostname of the cluster node.
        port (int): The port number for PAPI connections (default 8080).
        url (str): The base URL for API requests.
        connected (bool): Connection state of the session.
        services (list): List of authorized services for the current session.
        papiService (str): The API service being used (platform or namespace).
    """
    
    class PapiException(Exception):
        """Base exception class for all PAPI-related errors."""
        pass

    class PapiConnectionError(PapiException) :
        """Exception raised when a connection to the OneFS cluster fails."""
        def __init__(self, rObject) :
            if isinstance(rObject, requests.models.ConnectionError) :
                    self.status = rObject
                    self.text = str(rObject)
            else :
                raise TypeError("Unhandled connection error condition occured!")

    def __init__(self, HOST, username, password, port=8080, timeout=15, secure=False, papiService = 'platform', papiAgent = 'basePAPI Client for Python'):
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
        self.__session.headers.update({'content-type': 'application/json'})
        self.__session.headers.update({'User-Agent': papiAgent})
        self.__session.verify = secure
     
        # disable warnings on non secure certificates if ssl verification is turned off
        if(not secure):
            requests.packages.urllib3.disable_warnings()

    # the public session connect, disconnect and Status Update functions go here:

    def connect(self):
        """
        Establish a session connection to the OneFS Platform API.
        
        Authenticates with the cluster using the credentials provided during initialization
        and sets up CSRF token headers required for subsequent API calls.
        
        Returns:
            PapiResponse: Response object containing status code, headers, and body from
                the authentication request.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails.
        """
        myurl = self.url + self.__sessionURL
        try:
            response = self.__session.post(myurl, data=json.dumps(self.__auth), timeout=self.__timeout)
        except requests.exceptions.ConnectionError as e:
            raise self.PapiConnectionError(e)
        except Exception as e:
            raise self.PapiException(e)
        else :
            nHeader = { # add headers needed for CSRF support, without these we cannot use the session cookie for anything papi
                    'Origin': self.url,
                    'X-CSRF-Token': response.cookies.get('isicsrf')
            }
            self.__session.headers.update(nHeader)
            self.services = response.json()['services'] # load authorized services
            self.connected = True # set connection state
            myStatus = PapiResponse(
            status=response.status_code, headers=response.headers, uri=myurl
            )
            try:
                myStatus.body = response.json()
            except ValueError:
                pass
            return myStatus

    def disconnect(self):
        """
        Terminate the current session connection to the OneFS Platform API.
        
        Closes the authenticated session with the cluster and resets the connection state.
        
        Returns:
            PapiResponse: Response object containing status code, headers, and body from
                the session deletion request.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails during disconnect.
        """
        myurl = self.url + self.__sessionURL
        try:
            response = self.__session.delete(myurl)
        except requests.exceptions.ConnectionError as e:
            raise self.PapiConnectionError(e)
        except Exception as e:
            raise self.PapiException(e)
        else :
            self.connected = False
            myStatus = PapiResponse(
            status=response.status_code, headers=response.headers, uri=myurl
            )
            try:
                myStatus.body = response.json()
            except ValueError:
                pass
            return myStatus

    def getStatus(self):
        """
        Get the current session status from the OneFS Platform API.
        
        Retrieves information about the current authenticated session including
        session validity and authorized services.
        
        Returns:
            PapiResponse: Response object containing status code, headers, and body
                with session status information.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails.
        """
        myurl = self.url + self.__sessionURL
        try:
            response = self.__session.get(myurl)
        except requests.exceptions.ConnectionError as e:
            raise self.PapiConnectionError(e)
        except Exception as e:
            raise self.PapiException(e)
        myStatus = PapiResponse(
            status=response.status_code, headers=response.headers, uri=myurl
        )
        try:
            myStatus.body = response.json()
        except ValueError:
            pass
        return myStatus

    # the private function that does the actual work...

    def __request(self, method, uri, body={}, args={}, headers={}, serviceOverwrite = None ) :
        """
        Execute an HTTP request against the OneFS Platform API.
        
        Args:
            method: HTTP method to use (GET, PUT, POST, HEAD, DELETE).
            uri: API endpoint URI to request.
            body: Request body data to send as JSON. Defaults to empty dict.
            args: Query parameters to append to the URL. Defaults to empty dict.
            headers: Additional HTTP headers to include. Defaults to empty dict.
            serviceOverwrite: Override the default API service ('platform' or 'namespace').
                Defaults to None, which uses the session's default service.
        
        Returns:
            PapiResponse: Response object containing status code, headers, body, and URI.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails.
        """
        # if not already connected create the session to OneFS
        if(not self.connected): # connect
            self.connect()
        # create the request:
        thisService = {0: self.papiService, 1: serviceOverwrite}[serviceOverwrite in ['namespace', 'platform']] 
        myurl = self.url + thisService + uri
        if headers and isinstance(headers, dict) : # Add headers if specified... MUST be a dict!!!
            self.__session.headers.update(headers)
            # shall we validate the header format? and add error handling here?
        try: # Do the request.
            response = self.__session.request(method, url=myurl, params=args, json=body)
        except requests.exceptions.ConnectionError as e:
            raise self.PapiConnectionError(e)
        except Exception as e:
            raise self.PapiException(e)

        # clean up the response 
        output = PapiResponse(
            status=response.status_code, headers=response.headers, uri=myurl
        )

        try:
            output.body = response.json() # extract body json to dict
        except ValueError:
            pass    

        if headers and isinstance(headers, dict) : # Clean up API Call Specific Headers 
            for key in headers:
                if key in self.__session.headers:
                    del self.__session.headers[key]

        return output 

    #   define actual methods for PUT, POST, GET, HEAD and DELETE

    def get(self, uri, body=None, args=None, headers={}, serviceOverwrite=None):
        """
        Execute a GET request against the OneFS Platform API.
        
        Args:
            uri: API endpoint URI to request.
            body: Request body data to send as JSON. Defaults to None.
            args: Query parameters to append to the URL. Defaults to None.
            headers: Additional HTTP headers to include. Defaults to empty dict.
            serviceOverwrite: Override the default API service ('platform' or 'namespace').
                Defaults to None, which uses the session's default service.
        
        Returns:
            PapiResponse: Response object containing status code, headers, body, and URI.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails.
        """
        pResponse = self.__request('GET', uri, body, args, headers, serviceOverwrite)
        return pResponse

    def put(self, uri, body=None, args=None, headers={}, serviceOverwrite=None):
        """
        Execute a PUT request against the OneFS Platform API.
        
        Args:
            uri: API endpoint URI to request.
            body: Request body data to send as JSON. Defaults to None.
            args: Query parameters to append to the URL. Defaults to None.
            headers: Additional HTTP headers to include. Defaults to empty dict.
            serviceOverwrite: Override the default API service ('platform' or 'namespace').
                Defaults to None, which uses the session's default service.
        
        Returns:
            PapiResponse: Response object containing status code, headers, body, and URI.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails.
        """
        pResponse = self.__request('PUT', uri, body, args, headers, serviceOverwrite)
        return pResponse

    def head(self, uri, body=None, args=None, headers={}, serviceOverwrite=None):
        """
        Execute a HEAD request against the OneFS Platform API.
        
        Args:
            uri: API endpoint URI to request.
            body: Request body data to send as JSON. Defaults to None.
            args: Query parameters to append to the URL. Defaults to None.
            headers: Additional HTTP headers to include. Defaults to empty dict.
            serviceOverwrite: Override the default API service ('platform' or 'namespace').
                Defaults to None, which uses the session's default service.
        
        Returns:
            PapiResponse: Response object containing status code, headers, and URI.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails.
        """
        pResponse = self.__request('HEAD', uri, body, args, headers, serviceOverwrite)
        return pResponse

    def post(self, uri, body=None, args=None, headers={}, serviceOverwrite=None):
        """
        Execute a POST request against the OneFS Platform API.
        
        Args:
            uri: API endpoint URI to request.
            body: Request body data to send as JSON. Defaults to None.
            args: Query parameters to append to the URL. Defaults to None.
            headers: Additional HTTP headers to include. Defaults to empty dict.
            serviceOverwrite: Override the default API service ('platform' or 'namespace').
                Defaults to None, which uses the session's default service.
        
        Returns:
            PapiResponse: Response object containing status code, headers, body, and URI.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails.
        """
        pResponse = self.__request('POST', uri, body, args, headers, serviceOverwrite)
        return pResponse

    def delete(self, uri, body=None, args=None, headers={}, serviceOverwrite=None):
        """
        Execute a DELETE request against the OneFS Platform API.
        
        Args:
            uri: API endpoint URI to request.
            body: Request body data to send as JSON. Defaults to None.
            args: Query parameters to append to the URL. Defaults to None.
            headers: Additional HTTP headers to include. Defaults to empty dict.
            serviceOverwrite: Override the default API service ('platform' or 'namespace').
                Defaults to None, which uses the session's default service.
        
        Returns:
            PapiResponse: Response object containing status code, headers, body, and URI.
        
        Raises:
            PapiConnectionError: If the connection to the cluster fails.
        """
        pResponse = self.__request('DELETE', uri, body, args, headers, serviceOverwrite)
        return pResponse
    
    # allow context management as to be used in "with basepapi() as papi :"
    def __enter__(self) :
        return self
    
    def __exit__(self, *args, **kwargs):
        if self.connected :
            self.disconnect()