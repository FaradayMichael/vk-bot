-- migrate:up

ALTER TABLE triggers_answers
    ADD COLUMN attachment VARCHAR(255);


-- migrate:down

ALTER TABLE triggers_answers
    DROP COLUMN attachment;
