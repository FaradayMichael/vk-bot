-- migrate:up

CREATE TABLE triggers
(
    id    BIGSERIAL PRIMARY KEY,
    value VARCHAR(255)                NOT NULL UNIQUE,
    ctime TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc')
);

CREATE INDEX triggers_value_idx ON triggers (value);

CREATE TABLE answers
(
    id    BIGSERIAL PRIMARY KEY,
    value TEXT                        NOT NULL UNIQUE,
    ctime TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc')
);

CREATE INDEX answers_value_idx ON answers (value);

CREATE TABLE triggers_answers
(
    id         BIGSERIAL PRIMARY KEY,
    trigger_id BIGINT REFERENCES triggers (id) ON DELETE CASCADE NOT NULL,
    answer_id  BIGINT REFERENCES answers (id) ON DELETE CASCADE  NOT NULL
);

CREATE INDEX triggers_answers_trigger_id_idx ON triggers_answers (trigger_id);

-- migrate:down

DROP TABLE IF EXISTS triggers_answers;

DROP TABLE IF EXISTS answers;

DROP TABLE IF EXISTS triggers;
