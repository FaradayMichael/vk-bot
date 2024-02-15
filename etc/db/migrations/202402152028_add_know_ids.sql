-- migrate:up

CREATE TABLE know_ids
(
    id       BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

CREATE INDEX know_ids_name_idx ON know_ids(name);

-- migrate:down

DROP TABLE know_ids;
