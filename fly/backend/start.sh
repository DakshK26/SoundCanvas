#!/bin/bash
set -e

echo "Starting SoundCanvas Backend Initialization Script..."

# Function to find executable
find_exec() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "$1"
    elif [ -x "/usr/bin/$1" ]; then
        echo "/usr/bin/$1"
    elif [ -x "/usr/sbin/$1" ]; then
        echo "/usr/sbin/$1"
    else
        echo ""
    fi
}

# Locate MySQL/MariaDB binaries
MYSQLD_SAFE=$(find_exec "mariadbd-safe")
if [ -z "$MYSQLD_SAFE" ]; then
    MYSQLD_SAFE=$(find_exec "mysqld_safe")
fi

INSTALL_DB=$(find_exec "mariadb-install-db")
if [ -z "$INSTALL_DB" ]; then
    INSTALL_DB=$(find_exec "mysql_install_db")
fi

echo "Using mysqld_safe: $MYSQLD_SAFE"
echo "Using install_db: $INSTALL_DB"

# Initialize MySQL Data Directory if empty
if [ ! -d "/data/mysql/mysql" ]; then
    echo "Initializing MySQL data directory..."
    
    # Clean up potential partial initialization
    rm -rf /data/mysql/*
    mkdir -p /data/mysql
    chown -R mysql:mysql /data/mysql
    
    # Initialize DB
    if [ -n "$INSTALL_DB" ]; then
        echo "Running database initialization..."
        "$INSTALL_DB" --user=mysql --datadir=/data/mysql --auth-root-authentication-method=normal
    else
        echo "ERROR: Could not find mysql_install_db or mariadb-install-db"
        exit 1
    fi
    
    # Start MySQL temporarily to create DB and User
    echo "Starting MySQL for user creation..."
    "$MYSQLD_SAFE" --datadir=/data/mysql --skip-networking &
    PID=$!
    
    # Wait for MySQL to start
    echo "Waiting for MySQL to start..."
    for i in {1..30}; do
        if mysqladmin ping -u root --silent; then
            break
        fi
        echo "Waiting..."
        sleep 1
    done
    
    echo "Creating Database and User..."
    mysql -u root -e "CREATE DATABASE IF NOT EXISTS soundcanvas;"
    mysql -u root -e "CREATE USER IF NOT EXISTS 'soundcanvas'@'%' IDENTIFIED BY 'soundcanvas';"
    mysql -u root -e "CREATE USER IF NOT EXISTS 'soundcanvas'@'localhost' IDENTIFIED BY 'soundcanvas';"
    mysql -u root -e "GRANT ALL PRIVILEGES ON soundcanvas.* TO 'soundcanvas'@'%';"
    mysql -u root -e "GRANT ALL PRIVILEGES ON soundcanvas.* TO 'soundcanvas'@'localhost';"
    mysql -u root -e "FLUSH PRIVILEGES;"
    
    echo "MySQL Initialized."
    
    # Stop the temporary server
    if kill -0 $PID 2>/dev/null; then
        mysqladmin -u root shutdown
        wait $PID
    fi
fi

# Initialize MinIO Data Directory and bucket
mkdir -p /data/minio

# Create the bucket directory for MinIO (MinIO auto-detects directories as buckets)
mkdir -p /data/minio/soundcanvas-uploads

# Start Supervisor
echo "Starting Supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
