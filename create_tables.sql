-- Run this file to (re)create all the tables needed for the backend.

drop table if exists users;
create table users (
    id int primary key not null,
    username text not null unique,
    fullname text not null,
    password text not null,
    permissions text,
    email text not null unique,
    web text);

drop table if exists projects;
create table projects (
    id int primary key not null,
    creator int not null,
    title text not null,
    subtitle text,
    description text,
    url text,
    img_bg text,
    img1 text,
    img2 text);

drop table if exists profiles;
create table profiles (
    id int primary key,
    profile_name text);

drop table if exists user_profiles;
create table user_profiles (
    id_user int,
    id_profile int);

drop table if exists user_created_projects;
create table user_created_projects (
    id_user int,
    id_project int);

drop table if exists user_joined_projects;
create table user_joined_projects (
    id_user int,
    id_project int);

drop table if exists project_requested_profiles;
create table project_requested_profiles (
    id_project int,
    id_profile int);
