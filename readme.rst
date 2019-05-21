To start playing with a local sqlite database::

  sqlite3 smart.db < create_tables.sql
  sqlite3 smart.db < sample_data.sql


Example tests::

  curl -H "Content-Type: application/json" -X DELETE -u jordi:abc \
    -w '\nReturn code: %{http_code}\n' http://localhost:5000/users/3

  curl -H "Content-Type: application/json" -X POST -u jordi:abc \
    -d'{"id": 6, "creator": 1, "title":"boo"}' \
    -w '\nReturn code: %{http_code}\n' http://localhost:5000/projects

  curl -H "Content-Type: application/json" -X POST \
    -d '{"username": "jordi", "password": "abc"}' \
    -w '\nReturn code: %{http_code}\n' http://localhost:5000/login


To keep on going with bearer authentication, take the returned token and use
it in the next calls like::

  curl -H "Content-Type: application/json" -H "Authorization: Bearer $token" \
    -w '\nReturn code: %{http_code}\n' http://localhost:5000/users


Ideally, I'd like this kind of queries to work here too::

  https://play.dhis2.org/2.32.0/api/users/awtnYWiVEd5.json/dataValueSets.json?dataSet=pBOMPrpg1QX&period=201401&orgUnit=DiszpKrYNg8
