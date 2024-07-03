# basepapi
A simple OneFS PowerScale PAPI binding without the full SDK.

### Background
When I write simple tools to gather data from PowerScale Clusters I usualy use only a handfull of actual API Calls.
For this I prefer addressing the Platform API (PAPI) directly rather than to bother with a full blown SDK and the Version dependencies and overhead that comes with it.
You can call me oldfashioned. ;-)

However if you are looking for the official PowerScale SDK go here: https://github.com/Isilon/isilon_sdk

### Features:

- Supports: GET, HEAD, PUT, POST and DELETE operations against PowerScale / Isilons REST API Endpoints.
- Supports: REST access to system management (platform) as well as namespace ressources
- Leverages Session Authentication, hence best practice is to point it to a given Nodes IP Adress rather than a SmartConnect FQDN
- Returns a PapiResponse Class, containing: Status Code, response headers, and JSON Body as dict. auth session handling

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
except papi.papiConnectionError as e:
    print('Connection Error: %s' % e)
except papi.papiError as e:
    print('PAPI Error: %s' % e)
else :
    print(response.body)
```
Or in a papi context:
```python
from papi import basepapi
with basepapi('192.168.188.93', 'user', 'password', timeout=15) as papi :
    response = papi.get('/1/cluster/identity')
print(reponse.body)
```

Output:

```
{u'logon': {u'motd_header': u'', u'motd': u''}, u'description': u'', u'name': u'joshuatree'}	
```

### basepapi class internal structure:

```
{
#   class basepapi(builtins.object)

#   initialize with:
       papi(HOST, username, password, port=8080, timeout=15, secure=False, papiService='platform')

           'HOST'          :                           <type 'str'>,  # Stores the HOST / IP / FQDN of a PAPI Instance
           'username'      :                           username - user requires ISI_PRIV_LOGIN_PAPI and ISI_PRIV_NS_IFS_ACCESS RBAC permissions
           'password'      :                           password 
                           :                           NOTE: Username and password are stored in a dict (self.__auth) and only used during session setup.
           'timeout'       :                           <type 'int'>,  # Connection timeout (stored in self.__timeout)
           'papiService'   :                           <type 'str'>,  # stores PAPI Service to connect to must be either 'platform' (default) or 'namespace'
           'port'          :                           <type 'int'>,  # papi Port default: 8080
  
#   State Variables:

       'url'               :                           <type 'str'>,  # stores https url derived from HOST and port variable.
       'connected'         :                           <type 'bool'>, # stores connection state
       'services'          :                           <type 'list'>, # list of services a session is authorized to access ['platform', 'namespace']
   
#   Methods:

#   Session Setup and Management:
       connect(self)       :                           # create a authenticated session and request a session cookie
       getStatus(self)     :                           # reads Session state from PAPI Endpoint
       disconnect(self)    :                           # disconnects from a PAPI Session

#   http function wrappers:
       get(self, uri, body=None, args=None)          
       head(self, uri, body=None, args=None)         
       post(self, uri, body=None, args=None)
       put(self, uri, body=None, args=None)
       delete(self, uri, body=None, args=None)
}

```
### Papi Response 
```
	body 		<class 'requests.structures.CaseInsensitiveDict'>
	headers 	<class 'requests.structures.CaseInsensitiveDict'>
	rheaders 	<class 'requests.structures.CaseInsensitiveDict'>
	status 		<class 'int'>
	url 		<class 'str'>
```
### Exception handling
```
	papiConnectionError = <class 'papi.papi.papiConnectionError'>   => Catches generic connection errors 
	papiException = <class 'papi.papi.papiException'>               => Cathes any non connecton or non HTTP related exceptions 
	papiError = <class 'papi.papi.papiError'>                       => catches HTTP Errors as exception
```
Responses and Exceptions inherited from requests library.

### TODO(s):

- more testing
