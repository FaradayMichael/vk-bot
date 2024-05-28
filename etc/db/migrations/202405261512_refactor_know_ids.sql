-- migrate:up

CREATE TABLE IF NOT EXISTS know_ids_tmp
(
    id         BIGSERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    vk_id      BIGINT,
    discord_id BIGINT,
    note       TEXT,
    extra_data jsonb
);

INSERT INTO know_ids_tmp(name, vk_id)
SELECT name, id
FROM know_ids;

DROP TABLE know_ids;

ALTER TABLE know_ids_tmp
    RENAME TO know_ids;

-- migrate:down

DROP TABLE triggers_history;