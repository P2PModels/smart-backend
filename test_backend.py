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

def request(*args, **kwargs):
    "Return the json response from a url, accessed by basic authentication."
    mgr = req.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, urlbase, 'user1', 'abc')
    opener = req.build_opener(req.HTTPBasicAuthHandler(mgr))
    headers = {'Content-Type': 'application/json'}
    r = req.Request(urlbase + args[0], *args[1:], **kwargs, headers=headers)
    return json.loads(opener.open(r).read().decode('utf8'))


def get(*args, **kwargs):
    assert 'data' not in kwargs, 'Error: requests with data should be POST'
    return request(*args, **kwargs, method='GET')


def post(*args, **kwargs):
    assert 'data' in kwargs, 'Error: POST requests must have data'
    return request(*args, **kwargs, method='POST')


def put(*args, **kwargs):
    return request(*args, **kwargs, method='PUT')


def delete(*args, **kwargs):
    return request(*args, **kwargs, method='DELETE')


def jdumps(obj):
    return json.dumps(obj).encode('utf8')


def add_test_user():
    if 'id' in get('id/test_user'):
        raise Exception('User with id 1000 already exists.')

    data = jdumps({'username': 'test_user',
        'name': 'Random User', 'password': 'booo', 'email': 'test@ucm.es'})
    return post('users', data=data)


def del_test_user():
    uid = get('id/test_user')['id']
    return delete('users/%s' % uid)


def add_test_project():
    try:
        get('projects/1000')
        raise Exception('Project with id 1000 already exists.')
    except urllib.error.HTTPError as e:
        pass

    data = jdumps({'id': 1000, 'creator': 1, 'title': 'Test project'})
    return post('projects', data=data)


def del_test_project():
    return delete('projects/1000')


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
    def open_with_token(usernameOrEmail, password):
        data = jdumps({'usernameOrEmail': usernameOrEmail,
                       'password': password})
        res = post('login', data=data)
        auth_txt = 'Bearer ' + res['token']
        r = req.Request(urlbase + 'users', headers={'Authorization': auth_txt})
        req.urlopen(r)

    open_with_token('user1', 'abc')
    open_with_token('johnny@ucm.es', 'abc')


def test_get_users():
    res = get('users')
    assert type(res) == list
    assert all(x in res[0] for x in
        'id username name permissions web email'.split())
    assert res[0]['id'] == 1
    assert res[0]['username'] == 'user1'


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
    uid = get('id/test_user')['id']
    assert get('users/%s' % uid)['name'] == 'Random User'

    res = put('users/%s' % uid, data=jdumps({'name': 'Newman'}))
    assert res['message'] == 'ok'

    assert get('users/%s' % uid)['name'] == 'Newman'
    del_test_user()


def test_change_project():
    add_test_project()
    assert get('projects/1000')['title'] == 'Test project'

    res = put('projects/1000', data=jdumps({'title': 'changed'}))
    assert res['message'] == 'ok'

    assert get('projects/1000')['title'] == 'changed'
    del_test_project()


def test_add_del_participants():
    add_test_user()
    uid = get('id/test_user')['id']
    add_test_project()

    res = put('projects/1000', data=jdumps({'addParticipants': [uid]}))
    assert res['message'] == 'ok'

    assert uid in get('projects/1000')['participants']

    res = put('projects/1000', data=jdumps({'delParticipants': [uid]}))
    assert res['message'] == 'ok'

    del_test_project()
    del_test_user()


def test_get_info():
    assert get('info') == get('users/1')
