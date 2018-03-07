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


import os
import sys
from synchronizers.new_base.SyncInstanceUsingAnsible import SyncStep
from synchronizers.new_base.modelaccessor import VOLTDevice

from xosconfig import Config
from multistructlog import create_logger
from time import sleep
import requests

log = create_logger(Config().get('logging'))

# parentdir = os.path.join(os.path.dirname(__file__), "..")
# sys.path.insert(0, parentdir)
# sys.path.insert(0, os.path.dirname(__file__))

class SyncVOLTDevice(SyncStep):
    provides = [VOLTDevice]

    observes = VOLTDevice

    base_url = "http://172.20.0.1:8000/api/v1/"

    def sync_record(self, o):
        log.info("sync'ing device", object=str(o), **o.tologdict())

        data = {
            "type": "asfvolt16_olt",
            "host_and_port": "%s:%s" % (o.host, o.port)
        }

        r = requests.post(self.base_url + "/devices", json=data)

        if r.status_code != 200:
            raise Exception("Failed to add device: %s" % r.text)

        res = r.json()

        print res

        if not res['id']:
            raise Exception('VOLTHA Device Id is empty')
        else:
            o.device_id = res['id'];

        # enable device

        r = requests.post(self.base_url + "/devices/" + o.device_id + "/enable")

        if r.status_code != 200:
            raise Exception("Failed to activate device: %s" % r.text)

        # read state
        r = requests.get(self.base_url + "/devices/" + o.device_id)
        while r.json()['oper_status'] == "ACTIVATING":
            print("Waiting for device to activate")
            sleep(5)
            r = requests.get(self.base_url + "/devices/" + o.device_id)
            res = r.json()

            o.admin_state = res['admin_state']
            o.oper_status = res['oper_status']
            o.save()

    def delete_record(self, o):
        pass