-- migrate:up

CREATE TABLE gigachat_messages
(
    user_id          VARCHAR(255)             NOT NULL,
    ctime            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() at time zone 'utc'),

    id_              VARCHAR(255)                      DEFAULT NULL,
    role             VARCHAR(255)             NOT NULL,
    content          TEXT                     NOT NULL DEFAULT '',
    function_call    jsonb                             DEFAULT NULL,
    name             VARCHAR(255)                      DEFAULT NULL,
    attachments      jsonb                             DEFAULT NULL,
    data_for_context jsonb                             DEFAULT NULL
);

CREATE INDEX gigachat_messages_user_id_idx ON gigachat_messages (user_id);


-- migrate:down

DROP TABLE gigachat_messages;
