-- one row per song. PENDING -> QUEUED -> PROCESSING -> COMPLETED / FAILED
CREATE TABLE generations (
  id              CHAR(36) PRIMARY KEY,
  client_id       CHAR(36) NOT NULL,
  client_ip       VARCHAR(45) NOT NULL,  -- 45 = longest possible ipv6 string
  status          ENUM('PENDING','QUEUED','PROCESSING','COMPLETED','FAILED') NOT NULL,
  requested_genre VARCHAR(20),           -- NULL = model picks
  genre           VARCHAR(20),           -- what was actually used
  confidence      FLOAT,                 -- NULL if the user picked
  features        JSON,                  -- 8 floats, keeping them for retraining
  feedback        ENUM('UP','DOWN'),
  error_message   TEXT,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX history_lookup (client_id, created_at),     -- history page (+ the client_id half of the rate limit)
  INDEX rate_limit_lookup (client_ip, created_at),  -- the ip half of the rate limit
  INDEX stale_jobs (status, updated_at)             -- sweeper for lost jobs
);
