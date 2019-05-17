#!/usr/bin/env python3

"""
Keep the data of users and projects, and present a REST api to talk to the world.
"""

# TODO:
#   * Use bearer authentication (use python3-flask-httpauth MultiAuth, see
#     https://flask-httpauth.readthedocs.io/en/latest/).
#   * Make all the POST and PUT calls work.

# We will model our api on https://docs.dhis2.org/master/en/developer/html/webapi.html

# REST call examples:
# GET 	/device-management/devices : Get all devices
# POST 	/device-management/devices : Create a new device
#
# GET 	/device-management/devices/{id} : Get the device information identified by "id"
# PUT 	/device-management/devices/{id} : Update the device information identified by "id"
# DELETE	/device-management/devices/{id} : Delete device by "id"

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

app = None  # call initialize() to fill these up
db = None


class Users(Resource):
    def get(self, user_id=None):
        if not user_id:
            return get(db.connect(), 'id,name,password,mail,web', 'users')
        else:
            return get_user(user_id)

    def post(self):
        conn = db.connect()
        for user in request.json['users']:
            conn.execute('insert into users (%s) values (%s)' %
                         (','.join(user.keys()), ','.join(map(str, user.values()))))
        return {'message': 'ok'}

    def put(self, user_id):
        conn = db.connect()
        for user in request.json['users']:
            updates = ','.join('%r = %r' % k_v for k_v in user.items())
            conn.execute('update users set %s where id=%s' % (updates, user_id))
        return {'message': 'ok'}


class Projects(Resource):
    def get(self, project_id=None):
        if not project_id:
            return get(db.connect(),
                'id,creator,title,subtitle,description,url,img_bg,img1,img2',
                'projects')
        else:
            return get_project(project_id)


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
    users = get(conn, 'id,name,password,mail,web', 'users where id=%s' % uid)
    if len(users) != 1:
        return {'message': 'error: number of matching users is %d' % len(users)}
    user = users[0]
    user['profiles'] = get0(conn, 'profile_name',
        'profiles where id in '
            '(select id_profile from user_profiles where id_user=%s)' % uid)
    user['projects_created'] = (
        get0(conn, 'id_project', 'user_created_projects where id_user=%s' % uid))
    user['projects_joined'] = get0(conn, 'id_project',
        'user_joined_projects where id_user=%s' % uid)
    return user


def get_project(pid):
    "Return all the fields of a given project"
    conn = db.connect()
    project = get(conn,
        'id,creator,title,subtitle,description,url,img_bg,img1,img2',
        'projects where id=%s' % pid)[0]
    project['participants'] = get0(conn, 'id_user',
        'user_joined_projects where id_project=%s' % pid)
    project['requested_profiles'] = get0(conn, 'profile_name',
        'profiles where id in '
            '(select id_profile from project_requested_profiles where id_project=%s)' % pid)
    return project


def initialize(db_name='smart.db'):
    "Initialize the database and the flask app"
    global app, db
    db = sqlalchemy.create_engine('sqlite:///%s' % db_name)
    app = Flask(__name__)
    api = Api(app,
              errors={
                  'Exception': {
                      'status': 400,
                      'message': 'bad_request',
                      'some_description': 'Something wrong with request'
                  }})
    api.add_resource(Users, '/users', '/users/<string:user_id>')
    api.add_resource(Projects, '/projects', '/projects/<string:project_id>')


def create_db():
    "Create an empty database with the appropriate tables"
    conn = db.connect()
    for sql in open('create_tables.sql').read().split('\n\n'):
        try:
            conn.execute(sql)
        except sqlalchemy.exc.OperationalError as e:
            print(e.args[0])



if __name__ == '__main__':
    initialize()
    app.run(debug=True)
