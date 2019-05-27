-- Run this file to add sample values into the database.

insert into users values
    (1, 'jordibc', 'Jordi B.',
     'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
     'rxwrxwrxw', 'jordi@ucm.es', 'https://example1.org'),
    (2, 'sem', 'David L.',
     'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
     'r--r--r--', 'sem@ucm.es', 'https://example2.org'),
    (3, 'atenorio', 'Antonio T.',
     '3608bca1e44ea6c4d268eb6db02260269892c0b42b86bbf1e77a6fa16c3c9282',
     '---------', 'antonio@ucm.es', 'http://example3.org');

-- abc -> ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
-- 123 -> a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3
-- xyz -> 3608bca1e44ea6c4d268eb6db02260269892c0b42b86bbf1e77a6fa16c3c9282


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
