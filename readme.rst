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


Future Plans
------------

Ideally, I'd like queries that look like the following to work here too::

  https://play.dhis2.org/2.32.0/api/users/awtnYWiVEd5.json/dataValueSets.json?dataSet=pBOMPrpg1QX&period=201401&orgUnit=DiszpKrYNg8

This example comes from the `api of dhis2
<https://docs.dhis2.org/master/en/developer/html/webapi.html>`_.
