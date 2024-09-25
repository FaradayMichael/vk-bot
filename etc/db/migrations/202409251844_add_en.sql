-- migrate:up

ALTER TABLE discord_reply_commands
    ADD COLUMN en BOOLEAN DEFAULT TRUE;

ALTER TABLE know_ids
    ADD COLUMN en BOOLEAN DEFAULT TRUE;

ALTER TABLE triggers_answers
    ADD COLUMN en BOOLEAN DEFAULT TRUE;

-- migrate:down

ALTER TABLE triggers_answers
    DROP COLUMN en;

ALTER TABLE know_ids
    DROP COLUMN en;

ALTER TABLE discord_reply_commands
    DROP COLUMN en;
