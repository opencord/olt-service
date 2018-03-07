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

import json
from synchronizers.new_base.SyncInstanceUsingAnsible import SyncStep
from synchronizers.new_base.modelaccessor import VOLTService

from xosconfig import Config
from multistructlog import create_logger
from time import sleep
import requests
from requests.auth import HTTPBasicAuth

log = create_logger(Config().get('logging'))

class SyncOLTService(SyncStep):
    provides = [VOLTService]

    observes = VOLTService

    @staticmethod
    def format_url(url):
        if 'http' in url:
            return url
        else:
            return 'http://%s' % url

    @staticmethod
    def get_p_onos_info(o):
        return {
            'url': SyncOLTDevice.format_url(o.volt_service.p_onos_url),
            'user': o.volt_service.p_onos_user,
            'pass': o.volt_service.p_onos_pass
        }

    def sync_record(self, o):
        log.info("sync'ing olt service", object=str(o), **o.tologdict())

        if o.onu_provisioning == "allow_all":
            # tell ONOS to create the ONU device (POST xosapi/v1/volt/onudevices)
            pass
        if o.onu_provisioning == "pre_provisioned" or o.onu_provisioning == "oss":
            # tell ONOS to update the ONU device (POST xosapi/v1/volt/onudevices/<id>)
            # NOTE ONOS will need to find the <id>
            # NOTE if onu_provisioning == oss then XOS will need to make a call to the oss server to validate the onu
            pass


    def delete_record(self, o):
        pass
