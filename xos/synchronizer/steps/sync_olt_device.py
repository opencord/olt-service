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

    @staticmethod
    def format_url(url):
        if 'http' in url:
            return url
        else:
            return 'http://%s' % url

    @staticmethod
    def get_voltha_info(o):
        return {
            'url': SyncVOLTDevice.format_url(o.volt_service.voltha_url),
            'user': o.volt_service.voltha_user,
            'pass': o.volt_service.voltha_pass
        }

    @staticmethod
    def get_p_onos_info(o):
        return {
            'url': SyncVOLTDevice.format_url(o.volt_service.p_onos_url),
            'user': o.volt_service.p_onos_user,
            'pass': o.volt_service.p_onos_pass
        }


    def sync_record(self, o):
        log.info("sync'ing device", object=str(o), **o.tologdict())

        voltha_url = self.get_voltha_info(o)['url']
        data = {
            "type": o.device_type,
            "host_and_port": "%s:%s" % (o.host, o.port)
        }

        r = requests.post(voltha_url + "/api/v1/devices", json=data)

        if r.status_code != 200:
            raise Exception("Failed to add device: %s" % r.text)

        print r.text

        res = r.json()


        print res

        if not res['id']:
            raise Exception('VOLTHA Device Id is empty, this probably means that the device is already provisioned in VOLTHA')
        else:
            o.device_id = res['id'];

        # enable device

        r = requests.post(voltha_url + "/api/v1/devices/" + o.device_id + "/enable")

        if r.status_code != 200:
            raise Exception("Failed to activate device: %s" % r.text)
        else:
            print r.json()
            # o.admin_state = r.json()['admin_state']

        # read state
        r = requests.get(voltha_url + "/api/v1/devices/" + o.device_id).json()
        while r['oper_status'] == "ACTIVATING":
            print("Waiting for device to activate")
            sleep(5)
            r = requests.get(voltha_url + "/api/v1/devices/" + o.device_id).json()

        o.admin_state = r['admin_state']
        o.oper_status = r['oper_status']
        o.save()

    def delete_record(self, o):
        voltha_url = self.get_voltha_info(o)['url']
        if not o.device_id:
            log.error("Device %s has no device_id" % o.name)

        else:
            r = requests.post(voltha_url + "/api/v1/devices/" + o.device_id + "/disable")

            if r.status_code != 200:
                log.error("Failed to disable device: %s - %s" % (o.name, o.device_id), rest_responese=r.text, rest_status_code=r.status_code)
                raise Exception("Failed to disable device")

            r = requests.delete(voltha_url + "/api/v1/devices/" + o.device_id + "/delete")

            if r.status_code != 200:
                log.error("Failed to delete device: %s - %s" % (o.name, o.device_id), rest_responese=r.text, rest_status_code=r.status_code)
                raise Exception("Failed to delete device")