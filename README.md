# Pingou  

An NGINX logs parser written in python.

## How to run the image 

**1. Start the Database + NGINX**

To start the NGINX and Postgres: `./bin/db-prd.sh up postgres nginx`

**2. Start the listener and the worker**   

To start the listener: `./bin/db-prd.sh run --rm pingou listener < ./tests/files/config-prd.yml`
To start the worker: `./bin/db-prd.sh run --rm pingou worker < ./tests/files/config-prd.yml`

**3. Do a curl to NGINX**  

For instance: `curl http://127.0.0.1`



## Run tests  

1. Start the database and nginx with `./bin/db-dev.sh up postgres nginx`
2. Run the tests with `./bin/run-tests.sh`
