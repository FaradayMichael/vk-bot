-- migrate:up

CREATE TABLE polls
(
    id      BIGSERIAL PRIMARY KEY,
    en      BOOLEAN      NOT NULL       DEFAULT TRUE,
    ctime   TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() at time zone 'utc'),
    atime   TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
    dtime   TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
    data    jsonb        DEFAULT NULL,
    key     VARCHAR(255) NOT NULL,
    service INTEGER                     DEFAULT NULL
);

CREATE INDEX polls_service_key_en ON polls (service, key) WHERE en;

-- migrate:down

DROP TABLE polls;
