#!/usr/bin/env python3

"""
Keep the data of users and projects, and present a REST api to talk
to the world.
"""

# TODO:
#   * Use bearer authentication (use python3-flask-httpauth MultiAuth, see
#     https://flask-httpauth.readthedocs.io/en/latest/).
#   * Make the POST, PUT and DELETE calls work properly linking list of
#     projects, participants and so on (projects_created, projects_joined,
#     participants and requested_profiles).

# We will model our api on
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
#   name: str
#   password: str
#   mail: str
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


from flask import Flask, request
from flask_restful import Resource, Api
import sqlalchemy

db = None  # call initialize() to fill this up


class Users(Resource):
    def get(self, user_id=None):
        if not user_id:
            users = get(db.connect(), 'id,name,password,mail,web', 'users')
            return [nonempty(x) for x in users]
        else:
            return get_user(user_id)

    def post(self):
        conn = db.connect()
        for user in request.json['users']:
            conn.execute('insert into users %r values %r' %
                (tuple(user.keys()), tuple(user.values())))
        return {'message': 'ok'}

    def put(self, user_id):
        conn = db.connect()
        for user in request.json['users']:
            values = ','.join('%r=%r' % k_v for k_v in user.items())
            conn.execute('update users set %s where id=%d' % (values, user_id))
        return {'message': 'ok'}

    def delete(self, user_id):
        conn = db.connect()
        result = conn.execute('delete from users where id=%d' % user_id)
        if result.rowcount == 1:
            return {'message': 'ok'}
        else:
            return {'message': 'error: unknown user id %d' % user_id}, 409


class Projects(Resource):
    def get(self, project_id=None):
        if not project_id:
            return get(db.connect(),
                'id,creator,title,subtitle,description,url,img_bg,img1,img2',
                'projects')
        else:
            return get_project(project_id)

    def post(self):
        conn = db.connect()
        for project in request.json['projects']:
            conn.execute('insert into projects %r values %r' %
                (tuple(project.keys()), tuple(project.values())))
        return {'message': 'ok'}, 201

    def put(self, project_id):
        conn = db.connect()
        for project in request.json['projects']:
            values = ','.join('%r=%r' % k_v for k_v in project.items())
            conn.execute('update projects set %s where id=%d' %
                (values, project_id))
        return {'message': 'ok'}

    def delete(self, project_id):
        conn = db.connect()
        result = conn.execute('delete from projects where id=%d' % project_id)
        if result.rowcount == 1:
            return {'message': 'ok'}
        else:
            return {'message': 'error: unknown project id %d' % project_id}, 409


def get(conn, what, where):
    "Return result of the query 'select what from where' as a dict"
    res = conn.execute('select %s from %s' % (what, where)).fetchall()
    return [dict(zip(what.split(','), x)) for x in res]


def get0(conn, what, where):
    "Return a list of the selected elements from get()"
    return [x[what] for x in get(conn, what, where)]


def get_user(uid):
    "Return all the fields of a given user"
    conn = db.connect()

    users = get(conn, 'id,name,password,mail,web', 'users where id=%d' % uid)
    if len(users) == 0:
        return {'message': 'error: unknown user id %d' % uid}, 409

    user = users[0]

    user['profiles'] = get0(conn, 'profile_name',
        'profiles where id in '
            '(select id_profile from user_profiles where id_user=%d)' % uid)

    user['projects_created'] = get0(conn, 'id_project',
        'user_created_projects where id_user=%d' % uid)

    user['projects_joined'] = get0(conn, 'id_project',
        'user_joined_projects where id_user=%d' % uid)

    return nonempty(user)


def nonempty(d):
    "Return dictionary without the keys that have empty values"
    d_nonempty = {}
    for k, v in d.items():
        if v:
            d_nonempty[k] = d[k]
    return d_nonempty


def get_project(pid):
    "Return all the fields of a given project"
    conn = db.connect()

    projects = get(conn,
        'id,creator,title,subtitle,description,url,img_bg,img1,img2',
        'projects where id=%d' % pid)
    if len(projects) == 0:
        return {'message': 'error: unknown project id %d' % pid}, 409

    project = projects[0]

    project['participants'] = get0(conn, 'id_user',
        'user_joined_projects where id_project=%d' % pid)

    project['requested_profiles'] = get0(conn, 'profile_name',
        'profiles where id in '
        '  (select id_profile from project_requested_profiles '
        '   where id_project=%d)' % pid)

    return project


def initialize(db_name='smart.db'):
    "Initialize the database and the flask app"
    global db
    db = sqlalchemy.create_engine('sqlite:///%s' % db_name)
    app = Flask(__name__)
    errors = {
        'IntegrityError': {
            'status': 400,
            'message': 'bad_request',
            'description': 'Our database did not like that.'},
        'KeyError': {
            'status': 400,
            'message': 'missing_field',
            'description': 'Seems you forgot something in your request.'}}
    api = Api(app, errors=errors)
    api.add_resource(Users, '/users', '/users/<int:user_id>')
    api.add_resource(Projects, '/projects', '/projects/<int:project_id>')
    return app


def create_db():
    "Create an empty database with the appropriate tables"
    conn = db.connect()
    for sql in open('create_tables.sql').read().split('\n\n'):
        try:
            conn.execute(sql)
        except sqlalchemy.exc.OperationalError as e:
            print(e.args[0])



if __name__ == '__main__':
    app = initialize()
    app.run()
