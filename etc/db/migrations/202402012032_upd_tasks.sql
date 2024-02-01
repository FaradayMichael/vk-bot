-- migrate:up

ALTER TABLE vk_tasks
    ADD COLUMN created TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN started TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN done TIMESTAMP WITHOUT TIME ZONE;


-- migrate:down

ALTER TABLE vk_tasks
    DROP COLUMN created,
    DROP COLUMN started,
    DROP COLUMN done;
