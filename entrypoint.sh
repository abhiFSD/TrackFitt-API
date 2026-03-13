#!/bin/sh

# Initialize the database
python init-db.py

# Run the command passed to docker run
exec "$@" 
