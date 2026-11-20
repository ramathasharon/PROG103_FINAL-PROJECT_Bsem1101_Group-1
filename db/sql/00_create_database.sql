-- 00_create_database.sql
-- Run ONCE, connected to the default "postgres" database:
--     psql -U postgres -f 00_create_database.sql
-- (Not run by the Python app. Scripts 01 to 06 ARE run by the app at start-up.)

CREATE DATABASE permits_db
    ENCODING 'UTF8'
    TEMPLATE template0;
-- Then connect to it:  \c permits_db
