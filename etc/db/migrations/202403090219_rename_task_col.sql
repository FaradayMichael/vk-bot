-- migrate:up

ALTER TABLE vk_tasks
    RENAME COLUMN method TO func;

-- migrate:down

ALTER TABLE vk_tasks
    RENAME COLUMN func TO method;
