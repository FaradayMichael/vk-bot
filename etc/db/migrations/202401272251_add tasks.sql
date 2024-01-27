-- migrate:up

CREATE TABLE vk_tasks
(
    uuid   VARCHAR(255) PRIMARY KEY,
    method VARCHAR(255)                NOT NULL,
    args   TEXT,
    kwargs jsonb,
    errors TEXT,
    tries INTEGER NOT NULL DEFAULT 0,
    ctime  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc')
);

CREATE INDEX vk_tasks_uuid_idx ON vk_tasks (uuid);
CREATE INDEX vk_tasks_method_idx ON vk_tasks (method);


-- migrate:down

DROP TABLE vk_tasks;
