Smart Backend
=============

This program is intended to be run as a backend for `smart-projects
<https://github.com/P2PModels/smart-projects>`_. It
exposes a REST api to consult, create and change users and projects.


Initializing
------------

The default sql engine that it uses is `sqlite <https://www.sqlite.org/>`_,
with a local file named ``smart.db``. It can easily be changed to any other
(and should for scalability purposes).

Before running the backend the first time, you can initialize the database
this way::

  sqlite3 smart.db < create_tables.sql
  sqlite3 smart.db < sample_data.sql

Then you can run the backend directly with::

  ./backend.py

which will start it in debug mode. For a more serious usage, you can run it
for example with `gunicorn <https://gunicorn.org/>`_, as in::

  gunicorn backend:app

which will listen locally, or use ``-b 0.0.0.0:5000`` to listen to exterior
connections too.


Example calls
-------------

You can use ``curl`` to test the backend with commands like::

  curl -H "Content-Type: application/json" -X DELETE -u user1:abc \
    -w '\nReturn code: %{http_code}\n' http://localhost:5000/users/1

  curl -H "Content-Type: application/json" -X POST -u user1:abc \
    -d'{"id": 6, "name": "x1", "summary": "x2", "needs": "x3", "description": "x4"}' \
    -w '\nReturn code: %{http_code}\n' http://localhost:5000/projects

  curl -H "Content-Type: application/json" -X POST \
    -d '{"username": "user1", "password": "abc"}' \
    -w '\nReturn code: %{http_code}\n' http://localhost:5000/login


To keep on going with bearer authentication, take the returned token and use
it in the next calls like::

  curl -H "Content-Type: application/json" -H "Authorization: Bearer $token" \
    -w '\nReturn code: %{http_code}\n' http://localhost:5000/users


Tests
-----

You can also run a bunch of tests with::

  pytest-3

which will run all the functions that start with ``test_`` in the file
``test_backend.py``. You can also use the contents of that file to see
examples of how to use the api.


Api
---

The REST api has the following endpoints::

  /users
  /users/<id>
  /projects
  /projects/<id>
  /info
  /id/users/<username>
  /id/projects/<name>
  /login

They all support the GET method to request information. To **create** *users*
or *projects* use the POST method on the ``/users`` and ``/projects``
endpoints. To **modify** their values use the PUT method. To **delete** them
use the DELETE method.

The ``/info`` endpoint returns information about the currently logged user. The
``/id`` endpoint is useful to retrieve user and project ids from usernames and
project names.

Some of the endpoints and methods will require to be authenticated to use them.
You can use a registered user and password with Basic Authentication or Token
Authentication to access (you must use the ``/login`` endpoint first for that).

All the requests must send the information as json (with the
``Content-Type: application/json`` header). The replies are also json-encoded.

Most calls contain the *key* (property name) ``message`` in the response. If
the request was successful, its value will be ``ok``. If not, it will include
the text ``Error:`` with a description of the kind of error.

When creating a user or a profile an additional property ``id`` is returned,
with the id of the created object.

Finally, when using token authentication, the returned object contains the
properties ``id``, ``name``, ``email`` and (most importantly) ``token``
with the values referring to the successfully logged user. The value of
``token`` must be used in subsequent calls, with the header
``Authorization: Bearer <token>``, to stay logged as the same user.


Future Plans
------------

Ideally, I'd like queries that look like the following to work here too::

  https://play.dhis2.org/2.32.0/api/users/awtnYWiVEd5.json/dataValueSets.json?dataSet=pBOMPrpg1QX&period=201401&orgUnit=DiszpKrYNg8

This example comes from the `api of dhis2
<https://docs.dhis2.org/master/en/developer/html/webapi.html>`_.
