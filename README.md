# basepapi
A simple OneFS PowerScale PAPI binding without the full SDK.

### Background
When I write simple tools to gather data from PowerScale Clusters I usually use only a handful of actual API Calls.
For this I prefer addressing the Platform API (PAPI) directly rather than to bother with a full blown SDK and the Version dependencies and overhead that comes with it.
You can call me oldfashioned. ;-)

However if you are looking for the official PowerScale SDK go here: https://github.com/Isilon/isilon_sdk
And here: https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference
or here: https://developer.dell.com/apis/4088/versions/9.5.0/docs/1introduction.md

### Features:

- Supports: GET, HEAD, PUT, POST and DELETE operations against PowerScale / Isilon's REST API Endpoints.
- Supports: REST access to system management (platform) as well as namespace resources
- Leverages Session Authentication, hence best practice is to point it to a given Node's IP Address rather than a SmartConnect FQDN
- Returns a PapiResponse Class, containing: Status Code, response headers, and JSON Body as dict
- Automatic session management with context manager support

### How to integrate:

Requires: requests library - https://docs.python-requests.org/en/latest/

Install requests with pip:

```Bash
$ pip install requests
```

### Example Usage: 

```python
from papi import basepapi
papi = basepapi('192.168.188.93', 'user', 'password', timeout=15) 
try: 
   response = papi.get('/1/cluster/identity')
   response.raise_for_status()
except papi.papiConnectionError as e:
    print('Connection Error: %s' % e)
except papi.papiError as e:
    print('PAPI Error: %s' % e)
else:
    print(response.body)
```
Or using a context manager:
```python
from papi import basepapi
with basepapi('192.168.188.93', 'user', 'password', timeout=15) as papi:
    response = papi.get('/1/cluster/identity')
    print(response.body)
```

Output:

```
{'logon': {'motd_header': '', 'motd': ''}, 'description': '', 'name': 'joshuatree'}
```

### basepapi class internal structure:

```
class basepapi(builtins.object)

   Initialize with:
       basepapi(HOST, username, password, port=8080, timeout=15, secure=False, papiService='platform')

       Parameters:
           'HOST'          : <str>   # Hostname / IP / FQDN of a PAPI Instance
           'username'      : <str>   # User requires ISI_PRIV_LOGIN_PAPI and ISI_PRIV_NS_IFS_ACCESS RBAC permissions
           'password'      : <str>   # Password (stored securely, only used during session setup)
           'timeout'       : <int>   # Connection timeout in seconds (default: 15)
           'papiService'   : <str>   # PAPI Service: 'platform' (default) or 'namespace'
           'port'          : <int>   # PAPI Port (default: 8080)
           'secure'        : <bool>  # SSL certificate verification (default: False)
  
   Properties:
       'url'               : <str>   # HTTPS URL derived from HOST and port
       'connected'         : <bool>  # Connection state
       'services'          : <list>  # Services authorized for session ['platform', 'namespace']
   
   Methods:

   Session Management:
       connect()           : Create authenticated session and obtain session cookie
       getStatus()         : Read session state from PAPI Endpoint
       disconnect()        : Disconnect from PAPI session

   HTTP Methods:
       get(uri, body=None, args=None)     : HTTP GET request
       head(uri, body=None, args=None)    : HTTP HEAD request
       post(uri, body=None, args=None)    : HTTP POST request
       put(uri, body=None, args=None)     : HTTP PUT request
       delete(uri, body=None, args=None)  : HTTP DELETE request

   Context Manager:
       __enter__()         : Automatically connect on context entry
       __exit__()          : Automatically disconnect on context exit
```

### PapiResponse

```
class PapiResponse:
    body        : <dict>                                    # JSON response body
    headers     : <requests.structures.CaseInsensitiveDict> # Request headers sent
    rheaders    : <requests.structures.CaseInsensitiveDict> # Response headers received
    status      : <int>                                     # HTTP status code
    url         : <str>                                     # Request URL
```

### Exception Handling

```
papiConnectionError : Catches generic connection errors (network, timeout, etc.)
papiException       : Catches any non-connection or non-HTTP related exceptions
papiError           : Catches HTTP errors as exceptions (4xx, 5xx responses)
```

Responses and Exceptions are inherited from the requests library.

### TODO(s):

- More testing
- Add retry logic for transient failures
