-- migrate:up

ALTER TABLE send_on_schedule
    ADD COLUMN en BOOLEAN NOT NULL DEFAULT TRUE;


-- migrate:down

ALTER TABLE send_on_schedule
    DROP COLUMN en;
