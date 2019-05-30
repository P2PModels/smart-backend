#!/usr/bin/env python3

"""
Keep the data of users and projects, and present a REST api to talk
to the world.
"""

# TODO:
#   * Use user permissions to see & change data.
#   * Sanitize sql inputs.
#   * Catch and process well all cases when request.json is empty or invalid.

# We will take ideas for our api from
# https://docs.dhis2.org/master/en/developer/html/webapi.html

# REST call examples:
#   GET    /users       Get all users
#   GET    /users/{id}  Get the user information identified by "id"
#   POST   /users       Create a new user
#   PUT    /users/{id}  Update the user information identified by "id"
#   DELETE /users/{id}  Delete user by "id"

# The structure that we want to follow is:
#
# user
#   id: int
#   username: str
#   fullname: str
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
#   creator: int
#   title: str
#   subtitle: str
#   description: str
#   url: str
#   img_bg: str
#   img1: str
#   img2: str
#   participants: list of ints
#   requested_profiles: list of str


import hashlib
from flask import Flask, request, g
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from flask_restful import Resource, Api
import sqlalchemy
from itsdangerous import TimedJSONWebSignatureSerializer as JSONSigSerializer

db = None  # call initialize() to fill this up
serializer = None


# Set up the authentication (see https://flask-httpauth.readthedocs.io/).

auth_basic = HTTPBasicAuth()
auth_token = HTTPTokenAuth('Bearer')
auth = MultiAuth(auth_basic, auth_token)

@auth_basic.get_password
def get_pw(username):
    g.username = username
    passwords = dbget0('password', 'users where username=%r' % username)
    return passwords[0] if len(passwords) == 1 else None

@auth_basic.hash_password
def hash_pw(password):
    return sha256(password)  # we keep our passwords encrypted (hashed)

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
        fields = 'id,username,password,email'

        res = dbget(fields, 'users where username=%r' % name)
        if len(res) == 0:
            res = dbget(fields, 'users where email=%r' % name)
            if len(res) == 0:
                return None
        r0 = res[0]

        if r0['password'] == sha256(request.json['password']):
            token = serializer.dumps(r0['username']).decode('utf8')
            return {'id': r0['id'],
                    'name': r0['username'],
                    'email': r0['email'],
                    'token': token}
        else:
            return None


class Users(Resource):
    @auth.login_required
    def get(self, user_id=None):
        "Return info about the user (or all users if no id given)"
        if user_id is None:
            users = dbget('id,username,fullname,password,permissions,email,web',
                'users')
            return [strip(x) for x in users]
        else:
            return get_user(user_id)

    @auth.login_required
    def post(self):
        "Add user"
        if not request.json:
            raise KeyError
        cols, vals = zip(*request.json.items())
        dbexe('insert into users %r values %r' % (cols, vals))
        return {'message': 'ok'}

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
        exe = db.connect().execute
        res = exe('delete from users where id=%d' % user_id)
        if res.rowcount != 1:
            return {'message': 'error: unknown user id %d' % user_id}, 409

        exe('delete from user_profiles where id_user=%d' % user_id)
        exe('delete from user_created_projects where id_user=%d' % user_id)
        exe('delete from user_joined_projects where id_user=%d' % user_id)

        for pid in dbget0('id', 'projects where creator=%d' % user_id):
            del_project(pid)
        # NOTE: we could insted move them to a list of orphaned projects.

        return {'message': 'ok'}


class Projects(Resource):
    @auth.login_required
    def get(self, project_id=None):
        "Return info about the project (or all projects if no id given)"
        if project_id is None:
            projects = dbget(
                'id,creator,title,subtitle,description,url,img_bg,img1,img2',
                'projects')
            return [strip(x) for x in projects]
        else:
            return get_project(project_id)

    @auth.login_required
    def post(self):
        "Add project"
        if not request.json:
            raise KeyError
        cols, vals = zip(*request.json.items())
        dbexe('insert into projects %r values %r' % (cols, vals))
        return {'message': 'ok'}, 201

    @auth.login_required
    def put(self, project_id):
        "Modify project"
        add_participants(project_id, request.json.pop('addParticipants', None))
        del_participants(project_id, request.json.pop('delParticipants', None))
        if not request.json:
            return {'message': 'ok'}
        kvs = ','.join('%r=%r' % k_v for k_v in request.json.items())
        res = dbexe('update projects set %s where id=%d' % (kvs, project_id))
        if res.rowcount == 1:
            return {'message': 'ok'}
        else:
            return {'message': 'error: unknown project id %d' % project_id}, 409

    @auth.login_required
    def delete(self, project_id):
        "Delete project and all references to it"
        ids = dbget0('id', 'projects where id=%d' % project_id)
        if len(ids) != 1:
            return {'message': 'error: unknown project id %d' % project_id}, 409
        del_project(project_id)
        return {'message': 'ok'}


class Info(Resource):
    @auth.login_required
    def get(self):
        "Return info about the currently logged user"
        uid = dbget0('id', 'users where username=%r' % g.username)[0]
        return get_user(uid)


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
    users = dbget('id,username,fullname,password,permissions,email,web',
        'users where id=%d' % uid)
    if len(users) == 0:
        return {'message': 'error: unknown user id %d' % uid}, 409

    user = users[0]

    user['profiles'] = dbget0('profile_name',
        'profiles where id in '
            '(select id_profile from user_profiles where id_user=%d)' % uid)

    user['projects_created'] = dbget0('id_project',
        'user_created_projects where id_user=%d' % uid)

    user['projects_joined'] = dbget0('id_project',
        'user_joined_projects where id_user=%d' % uid)

    return strip(user)


def get_project(pid):
    "Return all the fields of a given project"
    projects = dbget(
        'id,creator,title,subtitle,description,url,img_bg,img1,img2',
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


def del_project(pid):
    "Delete a project and everywhere where it appears referenced"
    exe = db.connect().execute
    exe('delete from projects where id=%d' % pid)
    exe('delete from user_created_projects where id_project=%d' % pid)
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


def sha256(txt):
    return hashlib.sha256(txt.encode('utf8')).hexdigest()


# App initialization.

def initialize(db_name='smart.db', secret_key='top secret'):
    "Initialize the database and the flask app"
    global db, serializer
    db = sqlalchemy.create_engine('sqlite:///%s' % db_name)
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key
    serializer = JSONSigSerializer(app.config['SECRET_KEY'], expires_in=3600)
    api = Api(app, errors=error_messages)
    add_resources(api)
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



if __name__ == '__main__':
    app = initialize()
    app.run()
