-- One row per generation. The id is a UUID that is also the S3 key and the SQS deduplication id.
-- Each index matches one query in db.ts: history, the rate limit, and the stale-job sweep.
CREATE TABLE generations (
  id              CHAR(36) PRIMARY KEY,
  client_id       CHAR(36) NOT NULL,
  client_ip       VARCHAR(45) NOT NULL,  -- longest IPv6 string
  status          ENUM('PENDING','QUEUED','PROCESSING','COMPLETED','FAILED') NOT NULL,
  requested_genre VARCHAR(20),           -- NULL means let the model pick
  genre           VARCHAR(20),
  confidence      FLOAT,
  features        JSON,                  -- the 8 colour features for this song
  error_message   TEXT,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX history_lookup (client_id, created_at),
  INDEX rate_limit_lookup (client_ip, created_at),
  INDEX stale_jobs (status, updated_at)
);
