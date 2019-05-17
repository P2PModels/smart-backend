Example tests::

  curl -H "Content-Type: application/json" -X DELETE -w '%{http_code}' \
    http://localhost:5000/users/3

  curl -H "Content-Type: application/json" -X POST -w '%{http_code}' \
    -d'{"id": 6, "creator": 1, "title":"boo"}' http://localhost:5000/projects


Ideally, I'd like this kind of queries to work here too::

  https://play.dhis2.org/2.32.0/api/users/awtnYWiVEd5.json/dataValueSets.json?dataSet=pBOMPrpg1QX&period=201401&orgUnit=DiszpKrYNg8
