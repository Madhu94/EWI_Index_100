-- wipe.sql
PRAGMA foreign_keys = OFF;
DROP TABLE if exists indexlevels;
DROP TABLE if exists members;
DROP TABLE if exists changes;
DROP TABLE if exists marketdata;
DROP TABLE if exists settings;
VACUUM;
