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

#from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
#from twisted.internet.error import ConnectionRefusedError
#from txaioetcd import Client, CompVersion, Failed, KeySet, OpGet, OpSet, Transaction

#from pyvoltha.adapters.common.kvstore.etcd_client import EtcdClient

from etcd_client import EtcdClient
from kv_client import DEFAULT_TIMEOUT 

log = create_logger(Config().get("logging"))

class SyncTechnologyProfile(SyncStep):
    provides = [TechnologyProfile]

    observes = TechnologyProfile

    def test_etcd(self):
        etcd = EtcdClient(u'etcd-cluster.default.svc.cluster.local',2379)
        #status = etcd.status()

        #result = yield etcd.get(b'/xgspon/64')
        #if result.kvs:
        #    kv = result.kvs[0].value
        #    log.info("HARDIK value:", kv=kv)
        #else:
        #    log.info('key not found')        

        result = etcd._op_with_retry('GET', '/xgspon/65', None, DEFAULT_TIMEOUT)
        log.info("HARDIK: After test_etcd", result=result)
        #returnValue(result)

    def sync_record(self, o):
        log.info("HARDIK: Synching TechnologyProfile", object=str(o), **o.tologdict())

        log.info("HARDIK: TechnologyProfile: %s : %s" % (o.technology, o.tp_id))

        result = self.test_etcd()
        log.info("HARDIK: After test_etcd", result=result)
        #log.warning("HARDIK 123: TechnologyProfile: %s : %s" % (o.technology, o.tp_id))
        #print("HARDIK: TechnologyProfile: ", o.technology, o.tp_id)

        #request = requests.get("http://etcd-cluster.default.svc.cluster.local:2379/v2/keys/xgspon/64")
        #print("HARDIK: JSON: ", request.json())

        #etcd = Client(reactor, u'http://etcd-cluster.default.svc.cluster.local:2379')
        #print("HARDIK: 4")
        #print("HARDIK: 40")
        #status = yield etcd.status()
        #log.info("HARDIK: TechnologyProfile: Status: ", status=status)

        #result = yield etcd.get(b'/xgspon/64')
        #if result.kvs:
        #    kv = result.kvs[0].value
        #    log.info("HARDIK value:", kv=kv)
        #else:
        #    log.info('key not found')

        #print("HARDIK is here")

        #result1 = yield etcd.get(KeySet(b'/xgspon', prefix=True))
        #for kv1 in result1.kvs:
        #    log.info("HARDIK kv: ", kv1=kv1)
        #print("HARDIK: Client Status: ", status)

        #etcd = EtcdClient('etcd-cluster.default.svc.cluster.local', 2379)
        #print("HARDIK: EtcdClient")
        #result = etcd._op_with_retry('GET', '/xgspon/64', None, 1)
        #print("HARDIK: result: ", result)
