#
## Makefile to create the package tar.gz and push it to aws s3 bucket.
#
#
## Ignore implicit rules
.SUFFIXES:

.DEFAULT_GOAL := .done

REDIS_PORT=6439
LISTEN_PORT=8080
CURRENT_DATE=$(shell date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE='/var/tmp/app_log_$(CURRENT_DATE)'
PY_FILES := $(shell find wikiracer -iname "*.py")

lint:
	pylint $(PY_FILES)	

.PHONY: venv
venv: venv/bin/activate

# Install virtualenv for python 3.5, redis, redis-cli and required packages.
venv/bin/activate: requirements.txt
	test -d venv || virtualenv venv -p python3
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/bin/activate

# Start the project and run tests.
.PHONY: test
test: run
	source venv/bin/activate; nosetests wikiracer/test

# check if app is running, otherwise start in background mode
.PHONY: run
run: venv redis
	@echo 'start web server in background mode'
	curl -f http://localhost:$(LISTEN_PORT)/api/ping/ > /dev/null 2>&1 || (source venv/bin/activate; LISTEN_PORT=$(LISTEN_PORT) REDIS_PORT=$(REDIS_PORT) PYTHONPATH=$(PYTHON_PATH):. python3 wikiracer/app.py & >$(LOG_FILE) 2>&1)

.PHONY: redis
# test if redis is installed, otherwise install. Start redis (in daemon mode) if not started.
redis:
	test -f /usr/local/bin/redis-server || (wget http://download.redis.io/redis-stable.tar.gz;tar xvzf redis-stable.tar.gz;cd redis-stable;make)
	redis-cli -p $(REDIS_PORT) ping > /dev/null 2>&1 || redis-server --daemonize yes --dir . --port $(REDIS_PORT)

.PHONY: stop
# stop the redis server and app
stop:
	redis-cli -p $(REDIS_PORT) save > /dev/null 2>&1 || true
	redis-cli -p $(REDIS_PORT) shutdown > /dev/null 2>&1 || true
	ps -e -o "pid command" | grep 'app.py' | grep -v grep | awk '{print $1}' | xargs kill -9

.PHONY: clean
clean:
	rm -rf venv
	find . -iname "*.pyc" -delete
