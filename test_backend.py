"""
Test the functionality of backend.py.

The backend server must be running for the tests to run properly.

Run with "pytest-3".
"""

import urllib.request as req
import urllib.error
import json

urlbase = 'http://localhost:5000/'


# Helper functions.

def get(*args, **kwargs):
    "Return the json response from a url, accessed by basic authentication."
    mgr = req.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, urlbase, 'jordi', 'abc')
    opener = req.build_opener(req.HTTPBasicAuthHandler(mgr))
    headers = {'Content-Type': 'application/json'}
    r = req.Request(urlbase + args[0], *args[1:], **kwargs, headers=headers)
    return json.loads(opener.open(r).read())


def jdumps(obj):
    return json.dumps(obj).encode('utf8')


def add_test_user():
    try:
        get('users/1000')
        raise Exception('User with id 1000 already exists.')
    except urllib.error.HTTPError as e:
        pass

    data = jdumps({'id': 1000, 'name': 'test_user', 'password': 'booo'})
    return get('users', data=data)


def del_test_user():
    return get('users/1000', method='DELETE')


def add_test_project():
    try:
        get('projects/1000')
        raise Exception('Project with id 1000 already exists.')
    except urllib.error.HTTPError as e:
        pass

    data = jdumps({'id': 1000, 'creator': 1, 'title': 'Test project'})
    return get('projects', data=data)


def del_test_project():
    return get('projects/1000', method='DELETE')


# The tests.

def test_not_found():
    try:
        req.urlopen(urlbase)
    except urllib.error.HTTPError as e:
        assert (e.getcode(), e.msg) == (404, 'NOT FOUND')


def test_unauthorized():
    try:
        req.urlopen(urlbase + 'users')
    except urllib.error.HTTPError as e:
        assert (e.getcode(), e.msg) == (401, 'UNAUTHORIZED')


def test_auth_basic():
    get('users')


def test_auth_bearer():
    res = get('login', data=b'{"username": "jordi", "password": "abc"}')
    auth_txt = 'Bearer ' + res['access_token']
    r = req.Request(urlbase + 'users', headers={'Authorization': auth_txt})
    req.urlopen(r)


def test_get_users():
    res = get('users')
    assert type(res) == list
    assert all(x in res[0] for x in 'id name password web mail'.split())
    assert res[0]['id'] == 1
    assert res[0]['name'] == 'jordi'


def test_get_projects():
    res = get('projects')
    assert type(res) == list
    keys = 'id creator title subtitle description url img_bg img1 img2'.split()
    assert all(x in res[0] for x in keys)
    assert res[0]['id'] == 1
    assert res[0]['creator'] == 1


def test_add_del_user():
    res = add_test_user()
    assert res['message'] == 'ok'

    res = del_test_user()
    assert res['message'] == 'ok'


def test_add_del_project():
    res = add_test_project()
    assert res['message'] == 'ok'

    res = del_test_project()
    assert res['message'] == 'ok'


def test_change_user():
    add_test_user()

    res = get('users/1000', method='PUT', data=jdumps({'password': 'easy'}))
    assert res['message'] == 'ok'

    del_test_user()


def test_change_project():
    add_test_project()
    assert get('projects/1000')['title'] == 'Test project'

    res = get('projects/1000', method='PUT', data=jdumps({'title': 'changed'}))
    assert res['message'] == 'ok'

    assert get('projects/1000')['title'] == 'changed'
    del_test_project()


def test_add_del_participant():
    add_test_user()

    res = get('projects/1', method='PUT', data=jdumps({'addParticipant': 1000}))
    assert res['message'] == 'ok'

    res = get('projects/1', method='PUT', data=jdumps({'delParticipant': 1000}))
    assert res['message'] == 'ok'

    del_test_user()


def test_get_info():
    assert get('info') == get('users/1')
