
ISVENV := $(shell python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

build:
	docker build -t xosproject/volt-synchronizer:candidate -f xos/synchronizer/Dockerfile.synchronizer ./xos/synchronizer/

test:
ifeq ($(ISVENV), 1)
	pip install requests-mock
	pushd xos/synchronizer/steps/; nosetests test_sync_olt_device.py; popd;
else
	@echo "Please activate the virtualenv and the required libraries, you can do that using the 'scripts/setup_venv.sh' tool in the 'xos' repo"
endif
