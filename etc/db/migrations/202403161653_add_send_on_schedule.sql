-- migrate:up

CREATE TABLE send_on_schedule
(
    id           BIGSERIAL PRIMARY KEY,
    cron         VARCHAR(255)                NOT NULL,
    message_data jsonb                       NOT NULL,
    ctime        TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc')
);

-- migrate:down

DROP TABLE send_on_schedule;
