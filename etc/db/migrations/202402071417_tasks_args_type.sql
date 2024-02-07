-- migrate:up

ALTER TABLE vk_tasks
    DROP COLUMN args,
    ADD COLUMN args jsonb;



-- migrate:down

ALTER TABLE vk_tasks
    DROP COLUMN args,
    ADD COLUMN args TEXT;
