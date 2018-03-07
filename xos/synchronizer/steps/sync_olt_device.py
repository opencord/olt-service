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
from synchronizers.new_base.modelaccessor import VOLTDevice

from xosconfig import Config
from multistructlog import create_logger
from time import sleep
import requests
from requests.auth import HTTPBasicAuth

log = create_logger(Config().get('logging'))

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

    @staticmethod
    def get_of_id_from_device(o):
        voltha_url = SyncVOLTDevice.get_voltha_info(o)['url']

        r = requests.get(voltha_url + "/api/v1/logical_devices").json()

        for ld in r["items"]:
            if ld["root_device_id"] == o.device_id:
                return ld["id"]
        raise Exception("Can't find a logical device for device id: %s" % o.device_id)


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

        res = r.json()

        if not res['id']:
            raise Exception('VOLTHA Device Id is empty, this probably means that the device is already provisioned in VOLTHA')
        else:
            o.device_id = res['id'];

        # enable device

        r = requests.post(voltha_url + "/api/v1/devices/" + o.device_id + "/enable")

        if r.status_code != 200:
            raise Exception("Failed to enable device: %s" % r.text)

        # read state
        r = requests.get(voltha_url + "/api/v1/devices/" + o.device_id).json()
        while r['oper_status'] == "ACTIVATING":
            print("Waiting for device to activate")
            sleep(5)
            r = requests.get(voltha_url + "/api/v1/devices/" + o.device_id).json()

        o.admin_state = r['admin_state']
        o.oper_status = r['oper_status']

        # find of_id of device
        o.of_id = self.get_of_id_from_device(o)
        o.save()

        # add device info to P-ONOS
        data = {
          "devices": {
            o.of_id: {
              "basic": {
                "driver": o.driver
              },
              "accessDevice": {
                "uplink": o.uplink,
                "vlan": o.vlan
              }
            }
          }
        }

        onos= self.get_p_onos_info(o)

        r = requests.post(onos['url'] + '/onos/v1/network/configuration/', data=json.dumps(data), auth=HTTPBasicAuth(onos['user'], onos['pass']))

        if r.status_code != 200:
            log.error(r.text)
            raise Exception("Failed to add device %s into ONOS" % o.name)
        else:
            print r.json()

    def delete_record(self, o):
        voltha_url = self.get_voltha_info(o)['url']
        onos = self.get_p_onos_info(o)
        if not o.device_id:
            log.error("Device %s has no device_id" % o.name)

        else:

            # remove the device from ONOS
            r = requests.delete(onos['url'] + '/onos/v1/network/configuration/devices/' + o.of_id, auth=HTTPBasicAuth(onos['user'], onos['pass']))

            if r.status_code != 200:
                log.error("Failed to remove device from ONOS: %s - %s" % (o.name, o.of_id), rest_responese=r.text, rest_status_code=r.status_code)
                raise Exception("Failed to remove device in ONOS")

            # disable the device
            r = requests.post(voltha_url + "/api/v1/devices/" + o.device_id + "/disable")

            if r.status_code != 200:
                log.error("Failed to disable device in VOLTHA: %s - %s" % (o.name, o.device_id), rest_responese=r.text, rest_status_code=r.status_code)
                raise Exception("Failed to disable device in VOLTHA")

            # delete the device
            r = requests.delete(voltha_url + "/api/v1/devices/" + o.device_id + "/delete")

            if r.status_code != 200:
                log.error("Failed to delete device in VOLTHA: %s - %s" % (o.name, o.device_id), rest_responese=r.text, rest_status_code=r.status_code)
                raise Exception("Failed to delete device in VOLTHA")
