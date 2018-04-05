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

from synchronizers.new_base.SyncInstanceUsingAnsible import SyncStep
from synchronizers.new_base.modelaccessor import VOLTServiceInstance, ServiceInstance

from xosconfig import Config
from multistructlog import create_logger
import requests
from requests.auth import HTTPBasicAuth

log = create_logger(Config().get('logging'))

class SyncVOLTServiceInstance(SyncStep):
    provides = [VOLTServiceInstance]

    observes = VOLTServiceInstance

    def sync_record(self, o):

        si = ServiceInstance.objects.get(id=o.id)

        log.info("sync'ing device", object=str(o), **o.tologdict())

        log.info('----------------------- DEBUG -----------------------', c_tag=si.get_westbound_service_instance_properties('c_tag'))

        raise Exception('I want to fail')