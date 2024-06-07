-- migrate:up

CREATE TABLE discord_reply_commands
(
    command VARCHAR(255) PRIMARY KEY,
    text    TEXT    NOT NULL,
    reply   BOOLEAN NOT NULL DEFAULT TRUE
);


-- migrate:down

DROP TABLE discord_reply_commands;
