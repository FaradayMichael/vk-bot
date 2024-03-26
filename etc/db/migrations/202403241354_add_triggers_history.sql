-- migrate:up

CREATE TABLE triggers_history
(
    id                BIGSERIAL PRIMARY KEY,
    trigger_answer_id BIGINT                      NOT NULL REFERENCES triggers_answers (id),
    vk_id             BIGINT                      NOT NULL,
    message_data      jsonb                       NOT NULL,
    ctime             TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc')
);

CREATE INDEX triggers_history_vk_id_idx ON triggers_history (vk_id);

-- migrate:down

DROP TABLE triggers_history;
