-- Run this file to add sample values into the database.

insert into users values
    (1, 'user1', 'Johnny B. Goode',
     'pbkdf2:sha256:50000$713rFBmU$1e10a0e9b5fca0b4550b39dffd01931d8cdc64760d5995856e9c775e94e983dd',
     'rxwrxwrxw', 'johnny@ucm.es', 'https://example1.org'),
    (2, 'user2', 'Maria',
     'pbkdf2:sha256:50000$w4xHhhi8$75b2502e4680383c5fc89423e446b847021b52b086648897b8a6dcba60e771cb',
     'r--r--r--', 'maria@ucm.es', 'https://example2.org'),
    (3, 'user3', 'Debbie',
     'pbkdf2:sha256:50000$g2cIiryf$b0da4704216e5128544a831ba293adcc7aae3d730df9464cba5943fdf2b33c92',
     '---------', 'debbie@ucm.es', 'http://example3.org');

-- abc -> pbkdf2:sha256:50000$713rFBmU$1e10a0e9b...
-- 123 -> pbkdf2:sha256:50000$w4xHhhi8$75b2502e4...
-- xyz -> pbkdf2:sha256:50000$g2cIiryf$b0da47042...


insert into profiles values
    (1, 'programmer'),
    (2, 'drawing artist'),
    (3, 'musician'),
    (4, 'painter'),
    (5, 'magician');

insert into user_profiles values  -- id_user, id_profile
    (1, 1), (1, 3), (1, 5),
    (2, 1), (2, 4),
    (3, 2), (3, 3), (3, 4);

insert into projects values
    (1, 1, 'Superproject', 'A new and shiny project', 'This project does blah blah.', 'We need...',
    'https://project1.org', 'img_bg', 'img1.png', 'img2.png'),
    (2, 1, 'Project Meh', 'A new but crappy project', 'This project does not much.', 'We need...',
    'https://project2.org', 'img_bg', 'img1.png', 'img2.png'),
    (3, 2, 'Frontend', 'What will be shown', 'This project...', 'We need...',
    'https://project3.org', '1.png', '2.png', '3.jpg');

insert into user_organized_projects values  -- id_user, id_project
    (1, 1), (1, 2),
    (2, 3);

insert into user_joined_projects values  -- id_user, id_project
    (1, 3), (1, 2),
    (3, 1), (3, 2);

insert into project_requested_profiles values  -- id_project, id_profile
    (1, 1), (1, 2), (1, 3),
    (3, 3), (3, 4);
