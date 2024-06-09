-- migrate:up

ALTER TABLE discord_reply_commands
    ADD COLUMN channel_id BIGINT DEFAULT NULL;


-- migrate:down

ALTER TABLE discord_reply_commands
    DROP COLUMN channel_id;
