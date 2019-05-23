"""
Test the functionality of backend.py.

The backend server must be running for the tests to run properly.

Run with "pytest-3".
"""

import urllib.request as req
import urllib.error
import json


# Use basic authentication.
mgr = req.HTTPPasswordMgrWithDefaultRealm()
mgr.add_password(None, 'http://localhost:5000/', 'jordi', 'abc')
req.install_opener(req.build_opener(req.HTTPBasicAuthHandler(mgr)))


def test_get_users():
    contents = req.urlopen('http://localhost:5000/users').read()
    data = json.loads(contents)
    assert type(data) == list
    assert data[0]['id'] == 1
    assert data[0]['name'] == 'jordi'
