#!/usr/bin/env python3

"""
Keep the data of users and projects, and present a REST api to talk to the world.
"""

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


def create_db():
    "Create an empty database with the appropriate tables"
    conn = db.connect()
    sqls = """
create table projects (
    id int primary key not null,
    creator int not null,
    title text not null,
    subtitle text,
    description text,
    url text,
    imb_bg text,
    img1 text,
    img2 text
)

create table users (
    id int primary key not null,
    name text not null,
    password text not null,
    mail text,
    web text
)

create table profiles (
    id int primary key,
    profile_name text
)

create table user_profiles (
    id_user int,
    id_profile int
)

create table user_created_projects (
    id_user int,
    id_project int
)

create table user_joined_projects (
    id_user int,
    id_project int
)

create table project_participants (
    id_project int,
    id_user int
)

create table project_requested_profiles (
    id_project int,
    id_user int
)
""".split('\n\n')
    for sql in sqls:
        conn.execute(sql)


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
