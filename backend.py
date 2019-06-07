#!/usr/bin/env python3

"""
Keep the data of users and projects, and present a REST api to talk
to the world.

REST call examples:
  GET    /users       Get all users
  GET    /users/{id}  Get the user information identified by "id"
  POST   /users       Create a new user
  PUT    /users/{id}  Update the user information identified by "id"
  DELETE /users/{id}  Delete user by "id"
"""

# TODO:
#   * Check for valid keys only.
#   * Add and remove profiles to projects.
#   * Use user permissions to see & change data.
#   * Catch and process well all cases when request.json is empty or invalid.

# We will take ideas for our api from
# https://docs.dhis2.org/master/en/developer/html/webapi.html

# The structure that we want to follow is:
#
# user
#   id: int
#   username: str
#   name: str
#   password: str
#   permissions: str
#   email: str
#   web: str
#   profiles: list of str
#   projects_organized: list of projects
#   projects_joined: list of projects
#
# project
#   id: int
#   organizer: int
#   name: str
#   summary: str
#   description: str
#   needs: str
#   url: str
#   img_bg: str
#   img1: str
#   img2: str
#   participants: list of ints
#   requested_profiles: list of str


import os
from functools import partial
from contextlib import contextmanager
from flask import Flask, request, jsonify, g
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from flask_restful import Resource, Api
from flask_cors import CORS
import sqlalchemy
from itsdangerous import TimedJSONWebSignatureSerializer as JSONSigSerializer
from werkzeug.security import generate_password_hash, check_password_hash

db = None  # call initialize() to fill these up
serializer = None  # this one is used for the token auth


# Set up the authentication (see https://flask-httpauth.readthedocs.io/).

auth_basic = HTTPBasicAuth()
auth_token = HTTPTokenAuth('Bearer')
auth = MultiAuth(auth_basic, auth_token)

@auth_basic.verify_password
def verify_password(username, password):
    g.username = username
    res = dbget0('password', 'users where username=?', username)
    return check_password_hash(res[0], password) if res else False

@auth_token.verify_token
def verify_token(token):
    try:
        g.username = serializer.loads(token)
        return True
    except:
        return False


# Customized exception.

class InvalidUsage(Exception):
    def __init__(self, message, status_code=400):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code


# REST api.

class Login(Resource):
    def post(self):
        "Return info about the user if successfully logged, None otherwise"
        name = request.json['usernameOrEmail']
        fields = 'id,username,name,password,email'

        res = dbget(fields, 'users where username=?', name)
        if len(res) == 0:
            res = dbget(fields, 'users where email=?', name)
            if len(res) == 0:
                return {'message': 'Error: bad user'}, 401
        r0 = res[0]

        if check_password_hash(r0['password'], request.json['password']):
            token = serializer.dumps(r0['username']).decode('utf8')
            return {'id': r0['id'],
                    'name': r0['name'],
                    'email': r0['email'],
                    'token': token}
        else:
            return {'message': 'Error: bad password'}, 401


class Users(Resource):
    def get(self, user_id=None):
        "Return info about the user (or all users if no id given)"
        if user_id is None:
            return [get_user(uid) for uid in sorted(dbget0('id', 'users'))]
        else:
            return get_user(user_id)

    def post(self):
        "Add user"
        if not request.json:
            raise InvalidUsage('Missing json content')
        data = request.json.copy()

        cols_required = ['email', 'password']
        cols_valid = cols_required + ['username', 'name', 'web']

        if any(x not in data for x in cols_required):
            return {'message': 'user_missing_required',
                'description': 'Must have the fields %s' % cols_required}, 400
        if not all(x in cols_valid for x in data):
            return {'message': 'bad_entry',
                'description': 'Can only have the fields %s' % cols_valid}, 400

        data.setdefault('username', data['email'])  # username = email
        data['password'] = generate_password_hash(data['password'])
        data.setdefault('name', 'Random User')
        data['permissions'] = '---------'  # default permissions

        cols, vals = zip(*data.items())
        try:
            qs = '(%s)' % ','.join('?' * len(vals))
            dbexe('insert into users %r values %s' % (tuple(cols), qs), vals)
        except sqlalchemy.exc.IntegrityError as e:
            raise InvalidUsage('Error adding user: %s' % e)

        return {'message': 'ok'}, 201

    @auth.login_required
    def put(self, user_id):
        "Modify user"
        data = request.json.copy()
        # TODO: Check that only valid keys are passed.
        cols, vals = zip(*data.items())
        qs = ','.join('%s=?' % x for x in cols)
        res = dbexe('update users set %s where id=%d' % (qs, user_id), vals)
        if res.rowcount == 1:
            return {'message': 'ok'}
        else:
            return {'message': 'Error: unknown user id %d' % user_id}, 409

    @auth.login_required
    def delete(self, user_id):
        "Delete user and all references to her"
        with shared_connection([dbget0, dbexe]) as [get0, exe]:
            try:
                uid = get0('id', 'users where username=?', g.username)[0]
                assert user_id == uid or uid == 1
                # FIXME: last part should be something like "or has_permission()"
            except AssertionError:
                return {'message': 'Error: no permission to delete'}, 403

            res = exe('delete from users where id=?', user_id)
            if res.rowcount != 1:
                return {'message': 'Error: unknown user id %d' % user_id}, 409

            exe('delete from user_profiles where id_user=?', user_id)
            exe('delete from user_organized_projects where id_user=?', user_id)
            exe('delete from user_joined_projects where id_user=?', user_id)

            for pid in get0('id', 'projects where organizer=?', user_id):
                del_project(pid)
            # NOTE: we could insted move them to a list of orphaned projects.

        return {'message': 'ok'}


class Projects(Resource):
    def get(self, project_id=None):
        "Return info about the project (or all projects if no id given)"
        if project_id is None:
            return [get_project(pid) for pid in dbget0('id', 'projects')]
        else:
            return get_project(project_id)

    @auth.login_required
    def post(self):
        "Add project"
        if not request.json:
            raise InvalidUsage('Missing json content')
        data = request.json.copy()

        cols_required = ['id', 'name', 'summary', 'needs', 'description']
        cols_valid = cols_required + ['url', 'img_bg', 'img1', 'img2']

        if any(x not in data for x in cols_required):
            return {'message': 'project_missing_required',
                'description': 'Must have the fields %s' % cols_required}, 400
        if not all(x in cols_valid for x in data):
            return {'message': 'bad_entry',
                'description': 'Can only have the fields %s' % cols_valid}, 400

        with shared_connection([dbget0, dbexe]) as [get0, exe]:
            uid = get0('id', 'users where username=?', g.username)[0]
            data['organizer'] = uid

            cols, vals = zip(*data.items())
            qs = '(%s)' % ','.join('?' * len(vals))
            exe('insert into projects %r values %s' % (tuple(cols), qs), vals)
            exe('insert into user_organized_projects values (%d, %d)' %
                (uid, data['id']))

        return {'message': 'ok'}, 201

    @auth.login_required
    def put(self, project_id):
        "Modify project"
        if not request.json:
            raise KeyError
        data = request.json.copy()

        add_participants(project_id, data.pop('addParticipants', None))
        del_participants(project_id, data.pop('delParticipants', None))
        if not data:
            return {'message': 'ok'}
        cols, vals = zip(*data.items())
        qs = ','.join('%s=?' % x for x in cols)
        res = dbexe('update projects set %s where id=%d' % (qs, project_id), vals)
        if res.rowcount == 1:
            return {'message': 'ok'}
        else:
            return {'message': 'Error: unknown project id %d' % project_id}, 409

    @auth.login_required
    def delete(self, project_id):
        "Delete project and all references to it"

        if dbcount('projects where id=?', project_id) != 1:
            return {'message': 'Error: unknown project id %d' % project_id}, 409

        try:
            assert is_organizer(g.username, project_id)
            # NOTE: add "or has_permission()"
        except AssertionError:
            return {'message': 'Error: no permission to delete'}, 403

        del_project(project_id)
        return {'message': 'ok'}


class Info(Resource):
    @auth.login_required
    def get(self):
        "Return info about the currently logged user"
        uid = dbget0('id', 'users where username=?', g.username)[0]
        return get_user(uid)


class Id(Resource):
    def get(self, username):
        uids = dbget0('id', 'users where username=?', username)
        if not uids:
            return {'message': 'Error: unknown username %r' % username}, 400
        return {'id': uids[0]}



# Auxiliary functions.

def dbexe(command, *args, conn=None):
    "Execute a sql command (using a given connection if given)"
    conn = conn or db.connect()
    return conn.execute(command, *args)


def dbcount(where, *args, conn=None):
    "Return the number of rows from the given table (and given conditions)"
    res = dbexe('select count(*) from %s' % where, *args, conn=conn)
    return res.fetchone()[0]


def dbget(what, where, *args, conn=None):
    "Return result of the query 'select what from where' as a list of dicts"
    res = dbexe('select %s from %s' % (what, where), *args, conn=conn)
    return [dict(zip(what.split(','), x)) for x in res.fetchall()]


def dbget0(what, where, *args, conn=None):
    "Return a list of the single column of values from get()"
    assert ',' not in what, 'Use this function to select a single column only'
    return [x[what] for x in dbget(what, where, *args, conn=conn)]


@contextmanager
def shared_connection(functions):
    "Create a connection and yield the given functions but working with it"
    with db.connect() as conn:
        yield [partial(f, conn=conn) for f in functions]


def get_user(uid):
    "Return all the fields of a given user"
    with shared_connection([dbget, dbget0]) as [get, get0]:
        users = get('id,username,name,permissions,email,web',
            'users where id=?', uid)
        if len(users) == 0:
            return {'message': 'Error: unknown user id %d' % uid}, 409

        user = users[0]

        user['profiles'] = get0('profile_name',
            'profiles where id in '
                '(select id_profile from user_profiles where id_user=?)', uid)

        user['projects_created'] = get0('id_project',
            'user_organized_projects where id_user=?', uid)

        user['projects_joined'] = get0('id_project',
            'user_joined_projects where id_user=?', uid)

    return strip(user)


def get_project(pid):
    "Return all the fields of a given project"
    with shared_connection([dbget, dbget0]) as [get, get0]:
        projects = get(
            'id,organizer,name,summary,description,needs,url,img_bg,img1,img2',
            'projects where id=?', pid)
        if len(projects) == 0:
            return {'message': 'error: unknown project id %d' % pid}, 409

        project = projects[0]

        project['participants'] = get0('id_user',
            'user_joined_projects where id_project=?', pid)

        project['requested_profiles'] = get0('profile_name',
            'profiles where id in '
            '  (select id_profile from project_requested_profiles '
            '   where id_project=?)', pid)

    return strip(project)


def is_organizer(username, project_id):
    "Return True only if user is the organizer of the given project"
    with shared_connection([dbget0, dbcount]) as [get0, count]:
        uid = get0('id', 'users where username=?', username)[0]
        return count('user_organized_projects '
            'where id_user=? and id_project=?', (uid, project_id)) == 1


def del_project(pid):
    "Delete a project and everywhere where it appears referenced"
    exe = db.connect().execute
    exe('delete from projects where id=?', pid)
    exe('delete from user_organized_projects where id_project=?', pid)
    exe('delete from user_joined_projects where id_project=?', pid)
    exe('delete from project_requested_profiles where id_project=?', pid)


def strip(d):
    "Return dictionary without the keys that have empty values"
    d_stripped = {}
    for k, v in d.items():
        if v:
            d_stripped[k] = d[k]
    return d_stripped


def add_participants(pid, uids):
    "Add participants (with user id in uids) to a project (pid)"
    if not uids:
        return
    uids_str = '(%s)' % ','.join('%d' % x for x in uids)  # -> '(u1, u2, ...)'

    if dbcount('users where id in %s' % uids_str) != len(uids):
        raise InvalidUsage('Error: nonexisting user in %s' % uids_str)
    if dbcount('user_joined_projects '
        'where id_project=%d and id_user in %s' % (pid, uids_str)) != 0:
        raise InvalidUsage('Tried to add an already existing participant')

    values = ','.join('(%d, %d)' % (uid, pid) for uid in uids)
    dbexe('insert into user_joined_projects (id_user, id_project) '
        'values %s' % values)


def del_participants(pid, uids):
    "Remove participants (with user id in uids) from a project (pid)"
    if not uids:
        return
    uids_str = '(%s)' % ','.join('%d' % x for x in uids)  # -> '(u1, u2, ...)'

    if dbcount('user_joined_projects '
        'where id_project=%d and id_user in %s' % (pid, uids_str)) != len(uids):
        raise InvalidUsage('Error: nonexisting user in %s' % uids_str)

    dbexe('delete from user_joined_projects where '
        'id_user in %s and id_project=?' % uids_str, pid)


# App initialization.

def initialize(db_name='smart.db'):
    "Initialize the database and the flask app"
    global db, serializer
    db = sqlalchemy.create_engine('sqlite:///%s' % db_name)
    app = Flask(__name__)
    CORS(app)

    app.config['SECRET_KEY'] = os.urandom(256)
    serializer = JSONSigSerializer(app.config['SECRET_KEY'], expires_in=3600)

    api = Api(app)
    add_resources(api)

    @app.route('/')
    def description():
        return ('<html>\n<head>\n<title>Description</title>\n</head>\n'
            '<body>\n<pre>' + __doc__ + '</pre>\n</body>\n</html>')

    @app.errorhandler(InvalidUsage)
    def handle_invalid_usage(error):
        response = jsonify({'message': error.message})
        response.status_code = error.status_code
        return response

    return app


def add_resources(api):
    "Add all the REST endpoints"
    add = api.add_resource  # shortcut
    add(Login, '/login')
    add(Users, '/users', '/users/<int:user_id>')
    add(Projects, '/projects', '/projects/<int:project_id>')
    add(Info, '/info')
    add(Id, '/id/<username>')



app = initialize()

if __name__ == '__main__':
    app.run(debug=True)

# But for production it's better if we serve it with something like:
#   gunicorn backend:app
