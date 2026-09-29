CREATE TABLE generations (
  id              CHAR(36) PRIMARY KEY,
  client_id       CHAR(36) NOT NULL,
  client_ip       VARCHAR(45) NOT NULL,  -- longest IPv6 string
  status          ENUM('PENDING','QUEUED','PROCESSING','COMPLETED','FAILED') NOT NULL,
  requested_genre VARCHAR(20),
  genre           VARCHAR(20),
  confidence      FLOAT,
  features        JSON,
  feedback        ENUM('UP','DOWN'),
  error_message   TEXT,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX history_lookup (client_id, created_at),
  INDEX rate_limit_lookup (client_ip, created_at),
  INDEX stale_jobs (status, updated_at)
);
