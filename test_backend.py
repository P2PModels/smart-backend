"""
Test the functionality of backend.py.

The backend server must be running for the tests to run properly.

Run with "pytest-3".
"""

from contextlib import contextmanager
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


def add_test_user(fields=None):
    try:
        get('id/test_user')
        raise Exception('test_user already exists.')
    except urllib.error.HTTPError as e:
        pass

    data = {
        'username': 'test_user',
        'name': 'Random User', 'password': 'booo', 'email': 'test@ucm.es'}
    if fields:
        data.update(fields)

    return post('users', data=jdumps(data))


def del_test_user():
    uid = get('id/test_user')['id']
    return delete('users/%s' % uid)


@contextmanager
def test_user(fields=None):
    add_test_user(fields)
    try:
        yield
    finally:
        del_test_user()


def add_test_project(fields=None):
    try:
        pid = 1000 if not fields else fields.get('id', 1000)
        get('projects/%s' % pid)
        raise Exception('Project with id %s already exists.' % pid)
    except urllib.error.HTTPError as e:
        pass

    data = {
        'id': 1000, 'name': 'Test project',
        'summary': 'This is a summary.', 'needs': 'We need nothing here.',
        'description': 'This is an empty descritpion.'}
    if fields:
        data.update(fields)

    return post('projects', data=jdumps(data))


def del_test_project():
    return delete('projects/1000')


@contextmanager
def test_project(fields=None):
    add_test_project(fields)
    try:
        yield
    finally:
        del_test_project()


# The tests.

def test_not_found():
    try:
        url = urlbase + 'nonexistent'
        req.urlopen(url)
        raise Exception('We should not have found that url: %s' % url)
    except urllib.error.HTTPError as e:
        assert (e.getcode(), e.msg) == (404, 'NOT FOUND')


def test_unauthorized():
    try:
        url = urlbase + 'users/1'
        req.urlopen(req.Request(url, method='DELETE'))
        raise Exception('We should not have access to that url: %s' % url)
    except urllib.error.HTTPError as e:
        assert (e.getcode(), e.msg) == (401, 'UNAUTHORIZED')


def test_auth_basic():
    put('projects/1', data=jdumps({'name': 'Auth tested project'}))
    # If we are not authenticated, that request will raise an error.


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
    # If we are not authenticated, those requests will raise an error.


def test_get_users():
    res = get('users')
    assert type(res) == list
    assert all(x in res[0] for x in 'id username name permissions web'.split())
    assert res[0]['id'] == 1
    assert res[0]['username'] == 'user1'


def test_get_projects():
    res = get('projects')
    assert type(res) == list
    keys = 'id organizer name summary description url img_bg img1 img2'.split()
    assert all(x in res[0] for x in keys)
    assert res[0]['id'] == 1
    assert res[0]['organizer'] == 1


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


def test_add_del_project_with_profiles():
    res = add_test_project({'addProfiles': ['musician', 'painter']})
    assert res['message'] == 'ok'

    res = del_test_project()
    assert res['message'] == 'ok'


def test_change_user():
    with test_user():
        uid = get('id/test_user')['id']
        assert get('users/%s' % uid)['name'] == 'Random User'

        res = put('users/%s' % uid, data=jdumps({'name': 'Newman'}))
        assert res['message'] == 'ok'

        assert get('users/%s' % uid)['name'] == 'Newman'


def test_change_project():
    with test_project():
        assert get('projects/1000')['name'] == 'Test project'

        res = put('projects/1000', data=jdumps({'name': 'changed'}))
        assert res['message'] == 'ok'

        assert get('projects/1000')['name'] == 'changed'


def test_add_del_participants():
    with test_user():
        uid = get('id/test_user')['id']
        with test_project():
            res = put('projects/1000', data=jdumps({'addParticipants': [uid]}))
            assert res['message'] == 'ok'

            assert uid in get('projects/1000')['participants']

            res = put('projects/1000', data=jdumps({'delParticipants': [uid]}))
            assert res['message'] == 'ok'


def test_get_info():
    assert get('info') == get('users/1')


def test_existing_user():
    with test_user():
        try:
            data = jdumps({
                'username': 'test_user', 'name': 'Random User',
                'password': 'booo', 'email': 'test@ucm.es'})  # duplicated user
            post('users', data=data)
        except urllib.error.HTTPError as e:
            assert e.code == 400
            res = json.loads(e.file.read())
            assert res['message'].startswith('Error adding user')


def test_missing_email_in_new_user():
    try:
        data = jdumps({'username': 'test_user',
            'name': 'Random User', 'password': 'booo'})  # missing: email
        post('users', data=data)
    except urllib.error.HTTPError as e:
        assert e.code == 400
        res = json.loads(e.file.read())
        assert res['message'].startswith('Must have the fields')


def test_adding_invalid_fields_in_new_user():
    try:
        data = jdumps({'username': 'test_user',
            'name': 'Random User', 'password': 'booo',
            'email': 'test@ucm.es', 'invalid': 'should not go'})  # invalid
        post('users', data=data)
    except urllib.error.HTTPError as e:
        assert e.code == 400
        res = json.loads(e.file.read())
        assert res['message'].startswith('Can only have the fields')


def test_change_password():
    with test_user():
        # Change password.
        uid = get('id/test_user')['id']
        password_new = 'new_shiny_password'
        data = jdumps({'password': password_new})
        put('users/%s' % uid, data=data)

        # Use new password to connect.
        mgr = req.HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, urlbase, 'test_user', password_new)
        opener = req.build_opener(req.HTTPBasicAuthHandler(mgr))
        headers = {'Content-Type': 'application/json'}
        r = req.Request(urlbase + 'projects/1', headers=headers,
            method='PUT', data=jdumps({'name': 'Auth tested project'}))
        res = json.loads(opener.open(r).read().decode('utf8'))
        assert res['message'] == 'ok'
        # If we are not authenticated, that request will raise an error.


def test_add_del_profiles():
    profiles = ['programmer', 'magician']
    with test_project():
        res = put('projects/1000', data=jdumps({'addProfiles': profiles}))
        assert res['message'] == 'ok'

        assert all(x in get('projects/1000')['requested_profiles']
            for x in profiles)

        res = put('projects/1000', data=jdumps({'delProfiles': profiles}))
        assert res['message'] == 'ok'
