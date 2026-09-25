-- One row per song request. Status moves PENDING -> QUEUED -> PROCESSING -> COMPLETED or FAILED.
CREATE TABLE generations (
  id              CHAR(36) PRIMARY KEY,
  client_id       CHAR(36) NOT NULL,
  client_ip       VARCHAR(45) NOT NULL,  -- 45 characters fits the longest IPv6 address
  status          ENUM('PENDING','QUEUED','PROCESSING','COMPLETED','FAILED') NOT NULL,
  requested_genre VARCHAR(20),           -- the user's pick; NULL lets the model choose
  genre           VARCHAR(20),           -- the genre actually used
  confidence      FLOAT,                 -- the model's confidence; NULL when the user picked
  features        JSON,                  -- the image's 8 features, kept for retraining
  feedback        ENUM('UP','DOWN'),
  error_message   TEXT,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX history_lookup (client_id, created_at),     -- one browser's songs, newest first
  INDEX rate_limit_lookup (client_ip, created_at),  -- requests from one IP in the last hour
  INDEX stale_jobs (status, updated_at)             -- the worker's sweep for lost jobs
);
