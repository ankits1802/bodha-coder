# 0006 The first migration runs frozen SQL

Context: no local database exists to autogenerate migrations.

Choice: `0001_initial.py` executes `0001_initial.sql`, compiled once from the models with the
Postgres dialect, and seeds the places of service. Later migrations are written as explicit
operations. CI applies all migrations up and down against Postgres before the tests.
