-- migrate:up

CREATE TABLE discord_status_sessions
(
    id          BIGSERIAL PRIMARY KEY,
    started_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc'),
    finished_at TIMESTAMP WITH TIME ZONE          DEFAULT NULL,
    user_id     BIGINT                   NOT NULL,
    user_name   VARCHAR(255)             NOT NULL,
    status      VARCHAR(255)             NOT NULL,
    extra_data  jsonb                    NOT NULL DEFAULT '{}'
);


-- migrate:down

DROP TABLE discord_status_sessions;
