# Copyright 2019-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Configure shell
SHELL = bash -e -o pipefail

# Variables
VERSION                  ?= $(shell cat ./VERSION)
SERVICE_NAME             ?= $(notdir $(abspath .))
SYNCHRONIZER_NAME        ?= volt-synchronizer

## Docker related
DOCKER_REGISTRY          ?=
DOCKER_REPOSITORY        ?=
DOCKER_BUILD_ARGS        ?=
DOCKER_TAG               ?= ${VERSION}
DOCKER_IMAGENAME         := ${DOCKER_REGISTRY}${DOCKER_REPOSITORY}${SYNCHRONIZER_NAME}:${DOCKER_TAG}

## Docker labels. Only set ref and commit date if committed
DOCKER_LABEL_VCS_URL     ?= $(shell git remote get-url $(shell git remote))
DOCKER_LABEL_VCS_REF     ?= $(shell git diff-index --quiet HEAD -- && git rev-parse HEAD || echo "unknown")
DOCKER_LABEL_COMMIT_DATE ?= $(shell git diff-index --quiet HEAD -- && git show -s --format=%cd --date=iso-strict HEAD || echo "unknown" )
DOCKER_LABEL_BUILD_DATE  ?= $(shell date -u "+%Y-%m-%dT%H:%M:%SZ")

## Migration related - paths are relative to the xos subdirectory within this repo
XOS_DIR                  ?= "../../../xos"
SERVICES_DIR             ?= "../.."

all: help

docker-build: # @HELP build a docker image
	docker build $(DOCKER_BUILD_ARGS) \
    -t ${DOCKER_IMAGENAME} \
    --build-arg org_label_schema_version="${VERSION}" \
    --build-arg org_label_schema_vcs_url="${DOCKER_LABEL_VCS_URL}" \
    --build-arg org_label_schema_vcs_ref="${DOCKER_LABEL_VCS_REF}" \
    --build-arg org_label_schema_build_date="${DOCKER_LABEL_BUILD_DATE}" \
    --build-arg org_opencord_vcs_commit_date="${DOCKER_LABEL_COMMIT_DATE}" \
    -f Dockerfile.synchronizer .

docker-dev-build: # @HELP build a docker image using development library from xos (assumes the code is cloned with repo)
	mkdir -p tmp/
	cp -r ../../xos/* tmp/
	docker build $(DOCKER_BUILD_ARGS) \
	--build-arg DEV_LIBS=true \
	-t ${DOCKER_IMAGENAME} \
	--build-arg org_label_schema_version="${VERSION}" \
	--build-arg org_label_schema_vcs_url="${DOCKER_LABEL_VCS_URL}" \
	--build-arg org_label_schema_vcs_ref="${DOCKER_LABEL_VCS_REF}" \
	--build-arg org_label_schema_build_date="${DOCKER_LABEL_BUILD_DATE}" \
	--build-arg org_opencord_vcs_commit_date="${DOCKER_LABEL_COMMIT_DATE}" \
	-f Dockerfile.synchronizer .
	rm -r tmp/

docker-push: # @HELP push the docker image upstream
	docker push ${DOCKER_IMAGENAME}

test: test-unit test-migration test-xproto

test-unit: # @HELP runs unit tests
	tox

venv-service: # @HELP create a python virtual-environment with all the required dependencies
	virtualenv $@;\
    source ./$@/bin/activate ; set -u ;\
    pip install -r requirements.txt xosmigrate~=3.2.6

create-migration: venv-service # @HELP generate migrations
	source ./venv-service/bin/activate; set -u;\
    cd xos; xos-migrate --xos-dir ${XOS_DIR} --services-dir ${SERVICES_DIR} -s ${SERVICE_NAME}

test-migration: venv-service # @HELP check that migrations are up to date
	source ./venv-service/bin/activate; set -u;\
    cd xos; xos-migrate --xos-dir ${XOS_DIR} --services-dir ${SERVICES_DIR} -s ${SERVICE_NAME} --check

test-xproto: venv-service # @HELP validate xProto syntax
	source ./venv-service/bin/activate; set -u;\
    xosgenx --lint --strict xos/synchronizer/models/volt.xproto

clean: # @HELP remove all the build artifacts
	find . -name '*.pyc' | xargs rm -f
	rm -rf \
    .tox \
    venv-service \
    xos/.coverage \
    xos/coverage.xml \
    xos/nose2-results.xml \
    lib/xos-*

help:
	@grep -E '^.*: *# *@HELP' $(MAKEFILE_LIST) \
    | sort \
    | awk ' \
        BEGIN {FS = ": *# *@HELP"}; \
        {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}; \
    '
