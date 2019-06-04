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
#   * Use werkzeug.security hashed passwords.
#   * Add and remove profiles to projects.
#   * Use user permissions to see & change data.
#   * Sanitize sql inputs.
#   * Catch and process well all cases when request.json is empty or invalid.
#   * Maybe reuse the connection when there are several db* calls at once.
#   * Maybe use context managers to close cleanly the connections.

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
#   projects_created: list of projects
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
from flask import Flask, request, g
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
    res = dbget0('password', 'users where username=%r' % username)
    return check_password_hash(res[0], password) if res else False

@auth_token.verify_token
def verify_token(token):
    try:
        g.username = serializer.loads(token)
        return True
    except:
        return False


# Define the customized exceptions.

class NonexistingUserError(Exception):
    pass

class ExistingParticipantError(Exception):
    pass


# REST api.

class Login(Resource):
    def post(self):
        "Return info about the user if successfully logged, None otherwise"
        name = request.json['usernameOrEmail']
        fields = 'id,username,name,password,email'

        res = dbget(fields, 'users where username=%r' % name)
        if len(res) == 0:
            res = dbget(fields, 'users where email=%r' % name)
            if len(res) == 0:
                return None
        r0 = res[0]

        if check_password_hash(r0['password'], request.json['password']):
            token = serializer.dumps(r0['username']).decode('utf8')
            return {'id': r0['id'],
                    'name': r0['name'],
                    'email': r0['email'],
                    'token': token}
        else:
            return None


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
            raise KeyError
        data = request.json.copy()

        cols_required = ['email', 'password']
        cols_valid = cols_required + ['username', 'name', 'web']

        if any(x not in data for x in cols_required):
            return {'status': 400, 'message': 'user_missing_required',
                'description': 'Must have the fields %s' % cols_required}
        if not all(x in cols_valid for x in data):
            return {'status': 400, 'message': 'bad_entry',
                'description': 'Can only have the fields %s' % cols_valid}

        data.setdefault('username', data['email'])  # username = email
        data['password'] = generate_password_hash(data['password'])
        data.setdefault('name', 'Random User')
        data['permissions'] = '---------'  # default permissions

        cols, vals = zip(*data.items())
        dbexe('insert into users %r values %r' % (cols, vals))

        return {'message': 'ok'}, 201

    @auth.login_required
    def put(self, user_id):
        "Modify user"
        kvs = ','.join('%r=%r' % k_v for k_v in request.json.items())
        res = dbexe('update users set %s where id=%d' % (kvs, user_id))
        if res.rowcount == 1:
            return {'message': 'ok'}
        else:
            return {'message': 'error: unknown user id %d' % user_id}, 409

    @auth.login_required
    def delete(self, user_id):
        "Delete user and all references to her"
        try:
            uid = dbget0('id', 'users where username=%r' % g.username)[0]
            assert user_id == uid or uid == 1
            # FIXME: last part should be something like "or has_permission()"
        except AssertionError:
            return {'message': 'error: no permission to delete'}, 403

        exe = db.connect().execute
        res = exe('delete from users where id=%d' % user_id)
        if res.rowcount != 1:
            return {'message': 'error: unknown user id %d' % user_id}, 409

        exe('delete from user_profiles where id_user=%d' % user_id)
        exe('delete from user_organized_projects where id_user=%d' % user_id)
        exe('delete from user_joined_projects where id_user=%d' % user_id)

        for pid in dbget0('id', 'projects where organizer=%d' % user_id):
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
            raise KeyError
        data = request.json.copy()

        cols_required = ['id', 'name', 'summary', 'needs', 'description']
        cols_valid = cols_required + ['url', 'img_bg', 'img1', 'img2']

        if any(x not in data for x in cols_required):
            return {'status': 400, 'message': 'project_missing_required',
                'description': 'Must have the fields %s' % cols_required}
        if not all(x in cols_valid for x in data):
            return {'status': 400, 'message': 'bad_entry',
                'description': 'Can only have the fields %s' % cols_valid}

        uid = dbget0('id', 'users where username=%r' % g.username)[0]
        data['organizer'] = uid

        cols, vals = zip(*data.items())
        dbexe('insert into projects %r values %r' % (cols, vals))
        dbexe('insert into user_organized_projects values (%d, %d)' %
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
        kvs = ','.join('%r=%r' % k_v for k_v in data.items())
        res = dbexe('update projects set %s where id=%d' % (kvs, project_id))
        if res.rowcount == 1:
            return {'message': 'ok'}
        else:
            return {'message': 'error: unknown project id %d' % project_id}, 409

    @auth.login_required
    def delete(self, project_id):
        "Delete project and all references to it"

        if dbcount('projects where id=%d' % project_id) != 1:
            return {'message': 'error: unknown project id %d' % project_id}, 409

        try:
            assert is_organizer(g.username, project_id)
            # NOTE: add "or has_permission()"
        except AssertionError:
            return {'message': 'error: no permission to delete'}, 403

        del_project(project_id)
        return {'message': 'ok'}


class Info(Resource):
    @auth.login_required
    def get(self):
        "Return info about the currently logged user"
        uid = dbget0('id', 'users where username=%r' % g.username)[0]
        return get_user(uid)


class Id(Resource):
    def get(self, username):
        uids = dbget0('id', 'users where username=%r' % username)
        if not uids:
            return {'message': 'error: unknown username %r' % username}
        return {'id': uids[0]}



# Auxiliary functions.

def dbexe(command, conn=None):
    conn = conn or db.connect()
    return conn.execute(command)


def dbcount(where, conn=None):
    return dbexe('select count(*) from %s' % where, conn).fetchone()[0]


def dbget(what, where, conn=None):
    "Return result of the query 'select what from where' as a list of dicts"
    res = dbexe('select %s from %s' % (what, where), conn).fetchall()
    return [dict(zip(what.split(','), x)) for x in res]


def dbget0(what, where, conn=None):
    "Return a list of the single column of values from get()"
    assert ',' not in what, 'Use this function to select a single column only'
    return [x[what] for x in dbget(what, where, conn)]


def get_user(uid):
    "Return all the fields of a given user"
    users = dbget('id,username,name,permissions,email,web',
        'users where id=%d' % uid)
    if len(users) == 0:
        return {'message': 'error: unknown user id %d' % uid}, 409

    user = users[0]

    user['profiles'] = dbget0('profile_name',
        'profiles where id in '
            '(select id_profile from user_profiles where id_user=%d)' % uid)

    user['projects_created'] = dbget0('id_project',
        'user_organized_projects where id_user=%d' % uid)

    user['projects_joined'] = dbget0('id_project',
        'user_joined_projects where id_user=%d' % uid)

    return strip(user)


def get_project(pid):
    "Return all the fields of a given project"
    projects = dbget(
        'id,organizer,name,summary,description,needs,url,img_bg,img1,img2',
        'projects where id=%d' % pid)
    if len(projects) == 0:
        return {'message': 'error: unknown project id %d' % pid}, 409

    project = projects[0]

    project['participants'] = dbget0('id_user',
        'user_joined_projects where id_project=%d' % pid)

    project['requested_profiles'] = dbget0('profile_name',
        'profiles where id in '
        '  (select id_profile from project_requested_profiles '
        '   where id_project=%d)' % pid)

    return strip(project)


def is_organizer(username, project_id):
    "Return True iff user is the organizer of the given project"
    uid = dbget0('id', 'users where username=%r' % username)[0]
    print(uid)
    return dbcount('user_organized_projects where '
        'id_user=%d and id_project=%d' % (uid, project_id)) == 1


def del_project(pid):
    "Delete a project and everywhere where it appears referenced"
    exe = db.connect().execute
    exe('delete from projects where id=%d' % pid)
    exe('delete from user_organized_projects where id_project=%d' % pid)
    exe('delete from user_joined_projects where id_project=%d' % pid)
    exe('delete from project_requested_profiles where id_project=%d' % pid)


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
        raise NonexistingUserError
    if dbcount('user_joined_projects '
        'where id_project=%d and id_user in %s' % (pid, uids_str)) != 0:
        raise ExistingParticipantError

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
        raise NonexistingUserError

    dbexe('delete from user_joined_projects where '
        'id_user in %s and id_project=%d' % (uids_str, pid))


# App initialization.

def initialize(db_name='smart.db'):
    "Initialize the database and the flask app"
    global db, serializer
    db = sqlalchemy.create_engine('sqlite:///%s' % db_name)
    app = Flask(__name__)
    CORS(app)

    app.config['SECRET_KEY'] = os.urandom(256)
    serializer = JSONSigSerializer(app.config['SECRET_KEY'], expires_in=3600)

    api = Api(app, errors=error_messages)
    add_resources(api)

    @app.route('/')
    def description():
        return '<pre>' + __doc__ + '</pre>'

    return app


error_messages = {  # sent on different exceptions
    'ExistingParticipantError': {
        'status': 400,
        'message': 'existing_participant',
        'description': 'Tried to add an already existing participant.'},
    'NonexistingUserError': {
        'status': 400,
        'message': 'nonexisting_user',
        'description': 'Referenced a nonexisting user.'},
    'IntegrityError': {
        'status': 400,
        'message': 'bad_request',
        'description': 'Our database did not like that.'},
    'OperationalError': {
        'status': 400,
        'message': 'bad_field',
        'description': 'Seems you used a nonexisting field.'},
    'KeyError': {
        'status': 400,
        'message': 'missing_field',
        'description': 'Seems you forgot something in your request.'}}


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
