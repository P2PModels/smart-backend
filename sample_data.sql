-- Run this file to add sample values into the database.

insert into users values
    (1, 'jordi', 'abc', 'jordi@ucm.es', 'https://example1.org'),
    (2, 'sem', '123', 'sem@ucm.es', 'https://example2.org'),
    (3, 'antonio', 'xyz', 'antonio@ucm.es', 'http://example3.org');

insert into profiles values
    (1, 'coder'),
    (2, 'drawing artist'),
    (3, 'musician'),
    (4, 'painter');

insert into user_profiles values
    (1, 1),
    (1, 3),
    (2, 1),
    (2, 4),
    (3, 2),
    (3, 3),
    (3, 4);

insert into projects values
    (1, 1, 'Superproject', 'A new and shiny project', 'This project does blah blah.',
    'https://nope.org', 'img_bg', 'img1.png', 'img2.png'),
    (2, 1, 'Project Meh', 'A new but crappy project', 'This project does not much.',
    'https://another.world', 'img_bg', 'img1.png', 'img2.png'),
    (3, 2, 'Frontend', 'What will be shown', 'This project... whateves.',
    'https://p2pmod.eu', '1.png', '2.png', '3.jpg');

insert into user_created_projects values
    (1, 1),
    (1, 2),
    (2, 3);

insert into user_joined_projects values
    (1, 3),
    (3, 1),
    (3, 2);

insert into project_requested_profiles values
    (1, 1),
    (1, 2),
    (1, 3),
    (3, 3),
    (3, 4);
