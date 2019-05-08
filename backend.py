#!/usr/bin/env python3

"""
Keep the data of users and projects, and present a REST api to talk to the world.
"""

# user
#   id: int
#   name: str
#   password: str
#   mail: str
#   web: str
#   profiles: list of str
#   projects_created: list of projects
#   projects_joined: list of projects

# project
#   id: int
#   creator: int
#   participants: list of ints
#   title: str
#   subtitle: str
#   description: str
#   url: str
#   img_bg: str
#   img1: str
#   img2: str
#   requested_profiles: list of str

from flask import Flask, request
from flask_restful import Resource, Api
import sqlalchemy
import json

db = sqlalchemy.create_engine('sqlite:///smart.db')
app = Flask(__name__)
api = Api(app)


class Users(Resource):
    def get(self):
        conn = db.connect()
        query = conn.execute('select * from users')
        return {'users': [x for x in query.cursor.fetchall()]}


class Projects(Resource):
    def get(self):
        conn = db.connect()
        query = conn.execute('select * from projects')
        return {'projects': [x for x in query.cursor.fetchall()]}


api.add_resource(Users, '/users')
api.add_resource(Projects, '/projects')



if __name__ == '__main__':
    app.run()
