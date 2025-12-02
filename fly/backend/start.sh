#!/bin/bash
set -e

# Initialize MySQL Data Directory if empty
if [ ! -d "/data/mysql/mysql" ]; then
    echo "Initializing MySQL data directory..."
    mkdir -p /data/mysql
    chown -R mysql:mysql /data/mysql
    mysqld --initialize-insecure --user=mysql --datadir=/data/mysql
    
    # Start MySQL temporarily to create DB and User
    echo "Starting MySQL for initialization..."
    mysqld_safe --datadir=/data/mysql &
    PID=$!
    
    # Wait for MySQL to start
    sleep 10
    
    echo "Creating Database and User..."
    mysql -u root -e "CREATE DATABASE IF NOT EXISTS soundcanvas;"
    mysql -u root -e "CREATE USER 'soundcanvas'@'%' IDENTIFIED BY 'soundcanvas';"
    mysql -u root -e "GRANT ALL PRIVILEGES ON soundcanvas.* TO 'soundcanvas'@'%';"
    mysql -u root -e "FLUSH PRIVILEGES;"
    
    echo "MySQL Initialized."
    kill $PID
    wait $PID
fi

# Initialize MinIO Data Directory
mkdir -p /data/minio

# Start Supervisor
echo "Starting Supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
