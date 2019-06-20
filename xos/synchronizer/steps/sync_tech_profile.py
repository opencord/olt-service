# Copyright 2017-present Open Networking Foundation
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

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import Helpers

import requests
from multistructlog import create_logger
from requests.auth import HTTPBasicAuth
from xossynchronizer.modelaccessor import TechnologyProfile, model_accessor
from xossynchronizer.steps.syncstep import SyncStep
from xosconfig import Config

import etcd3

# TODO store ETCD_HOST_URL and ETCD_PORT in the vOLT Service model
ETCD_HOST_URL = 'etcd-cluster.default.svc.cluster.local'
ETCD_PORT = 2379
PREFIX = "service/voltha/technology_profiles"

log = create_logger(Config().get("logging"))

class SyncTechnologyProfile(SyncStep):
    provides = [TechnologyProfile]

    observes = TechnologyProfile

    def update_etcd(self, operation, key, value):
        log.info('Update Etcd store: ', operation=operation, key=key, value=value)

        etcd = etcd3.client(host=ETCD_HOST_URL, port=ETCD_PORT)
        if operation == 'PUT':
           etcd.put(PREFIX + key, value)
           log.info('Technology Profile [%s] saved successfully to Etcd store' % (PREFIX + key))
        elif operation == 'DELETE':
           if False == etcd.delete(PREFIX + key):
               log.error('Error while deleting Technology Profile [%s] from Etcd store' % key)
               raise Exception('Failed to delete Technology Profile')
           else:
               log.info('Technology Profile [%s] deleted successfully from Etcd store' % key)
        else:
           log.warning('Invalid or unsupported Etcd operation: %s' % operation)

    def sync_record(self, model):
        log.info('Synching TechnologyProfile', object=str(model), **model.tologdict())

        log.info('TechnologyProfile: %s : %s' % (model.technology, model.profile_id))

        tp_key = u'/' + model.technology + u'/' + str(model.profile_id)
        self.update_etcd('PUT', tp_key, model.profile_value)

    def delete_record(self, model):
        log.info('Deleting TechnologyProfile', object=str(model), **model.tologdict())

        log.info('TechnologyProfile: %s : %s' % (model.technology, model.profile_id))

        tp_key = u'/' + model.technology + u'/' + str(model.profile_id)
        self.update_etcd('DELETE', tp_key, None)

