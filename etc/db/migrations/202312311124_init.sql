-- migrate:up

CREATE TABLE users
(
    id       BIGSERIAL PRIMARY KEY,
    en       BOOLEAN                     NOT NULL DEFAULT true,

    username VARCHAR(255)                NOT NULL,
    email    VARCHAR(255)                NOT NULL,
    password VARCHAR(255)                NOT NULL,
    is_admin BOOLEAN                     NOT NULL DEFAULT FALSE,

    ctime    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc'),
    atime    TIMESTAMP WITHOUT TIME ZONE          DEFAULT NULL,
    dtime    TIMESTAMP WITHOUT TIME ZONE          DEFAULT NULL
);

CREATE INDEX users_username_idx ON users (username) WHERE en = TRUE;
CREATE INDEX users_email_idx ON users (email) WHERE en = TRUE;

-- migrate:down

DROP TABLE IF EXISTS users;
