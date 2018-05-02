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

    def sync_record(self, o):
        log.info("synching OLT service", object=str(o), **o.tologdict())

        if o.onu_provisioning == "allow_all":
            # TODO: Tell ONOS to create the ONU device (POST xosapi/v1/volt/onudevices)
            pass
        if o.onu_provisioning == "pre_provisioned" or o.onu_provisioning == "oss":
            # TODO: Tell ONOS to update the ONU device (POST xosapi/v1/volt/onudevices/<id>)
            # ONOS will need to find the <id>
            # if onu_provisioning == oss then XOS will need to make a call to the oss server to validate the ONU
            pass

    def delete_record(self, o):
        pass
