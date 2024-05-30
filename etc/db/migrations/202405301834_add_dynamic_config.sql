-- migrate:up

CREATE TABLE dynamic_config
(
    id   INTEGER PRIMARY KEY,
    data jsonb NOT NULL DEFAULT '{}'
);

INSERT INTO dynamic_config
VALUES (1, '{}');

-- migrate:down

DROP TABLE dynamic_config;