-- migrate:up


CREATE TABLE triggers_answers
(
    id      BIGSERIAL PRIMARY KEY,
    trigger VARCHAR(255)                NOT NULL,
    answer  TEXT                        NOT NULL,
    ctime   TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc')
);

CREATE UNIQUE INDEX triggers_answers_trigger_answer_unique ON triggers_answers (trigger, answer);

CREATE INDEX triggers_answers_trigger_idx ON triggers_answers (trigger);

CREATE INDEX triggers_answers_answer_idx ON triggers_answers (answer);


-- migrate:down

DROP TABLE IF EXISTS triggers_answers;
