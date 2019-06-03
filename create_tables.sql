-- Run this file to (re)create all the tables needed for the backend.

drop table if exists users;
create table users (
    id integer primary key autoincrement,
    username text not null unique,
    name text not null,
    password text not null,
    permissions text,
    email text not null unique,
    web text);

drop table if exists projects;
create table projects (
    id integer primary key not null,
    creator integer not null,
    title text not null,
    subtitle text,
    description text,
    url text,
    img_bg text,
    img1 text,
    img2 text);

drop table if exists profiles;
create table profiles (
    id integer primary key autoincrement,
    profile_name text);

drop table if exists user_profiles;
create table user_profiles (
    id_user integer,
    id_profile integer);

drop table if exists user_created_projects;
create table user_created_projects (
    id_user integer,
    id_project integer);

drop table if exists user_joined_projects;
create table user_joined_projects (
    id_user integer,
    id_project integer);

drop table if exists project_requested_profiles;
create table project_requested_profiles (
    id_project integer,
    id_profile integer);
