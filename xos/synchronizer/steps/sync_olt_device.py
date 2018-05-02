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
from synchronizers.new_base.modelaccessor import OLTDevice

from xosconfig import Config
from multistructlog import create_logger
from time import sleep
import requests
from requests.auth import HTTPBasicAuth
from helpers import Helpers

log = create_logger(Config().get('logging'))

class SyncOLTDevice(SyncStep):
    provides = [OLTDevice]
    observes = OLTDevice

    @staticmethod
    def get_ids_from_logical_device(o):
        voltha = Helpers.get_voltha_info(o.volt_service)

        request = requests.get("%s:%d/api/v1/logical_devices" % (voltha['url'], voltha['port']))

        if request.status_code != 200:
            raise Exception("Failed to retrieve logical devices from VOLTHA: %s" % request.text)

        response = request.json()

        for ld in response["items"]:
            if ld["root_device_id"] == o.device_id:
                o.of_id = ld["id"]
                o.dp_id = "of:%s" % (Helpers.datapath_id_to_hex(ld["datapath_id"])) # Convert to hex
                return o

        raise Exception("Can't find a logical device for device id: %s" % o.device_id)


    def sync_record(self, o):
        log.info("Synching device", object=str(o), **o.tologdict())

        voltha = Helpers.get_voltha_info(o.volt_service)
        onos_voltha = Helpers.get_onos_voltha_info(o.volt_service)
        onos_voltha_basic_auth = HTTPBasicAuth(onos_voltha['user'], onos_voltha['pass'])

        # If the device has feedback_state is already present in voltha
        if not o.device_id and not o.admin_state and not o.oper_status and not o.of_id:
            log.info("Pushing device to VOLTHA", object=str(o), **o.tologdict())

            data = {
                "type": o.device_type,
                "host_and_port": "%s:%s" % (o.host, o.port)
            }

            if o.device_type == 'simulated_olt':
                # Simulated devices will not accept host and port. This is for test only
                data.pop('host_and_port')
                data['mac_address'] = "00:0c:e2:31:40:00"

            log.info("Pushing OLT to Voltha", data=data)

            request = requests.post("%s:%d/api/v1/devices" % (voltha['url'], voltha['port']), json=data)

            if request.status_code != 200:
                raise Exception("Failed to add device: %s" % request.text)

            log.info("Add device response", text=request.text)

            res = request.json()

            log.info("Add device json res", res=res)

            if not res['id']:
                raise Exception('VOLTHA Device Id is empty, this probably means that the device is already provisioned in VOLTHA')
            else:
                o.device_id = res['id'];

            # Enable device
            request = requests.post("%s:%d/api/v1/devices/%s/enable" % (voltha['url'], voltha['port'], o.device_id))

            if request.status_code != 200:
                raise Exception("Failed to enable device: %s" % request.text)

            # Read state
            request = requests.get("%s:%d/api/v1/devices/%s" % (voltha['url'], voltha['port'], o.device_id)).json()
            while request['oper_status'] == "ACTIVATING":
                log.info("Waiting for device %s (%s) to activate" % (o.name, o.device_id))
                sleep(5)
                request = requests.get("%s:%d/api/v1/devices/%s" % (voltha['url'], voltha['port'], o.device_id)).json()

            o.admin_state = request['admin_state']
            o.oper_status = request['oper_status']

            # Find the of_id of the device
            o = self.get_ids_from_logical_device(o)
            o.save()
        else:
            log.info("Device already exists in VOLTHA", object=str(o), **o.tologdict())


        # Do we need to move this synchronization in a PON_PORT specific step?
        # For now, we assume that each OLT has only one port
        vlan = o.ports.all()[0].s_tag

        # Add device info to onos-voltha
        data = {
          "devices": {
            o.dp_id: {
              "basic": {
                "driver": o.driver
              },
              "accessDevice": {
                "uplink": o.uplink,
                "vlan": vlan
              }
            }
          }
        }

        request = requests.post("%s:%d/onos/v1/network/configuration/" % (onos_voltha['url'], onos_voltha['port']), data=json.dumps(data), auth=onos_voltha_basic_auth)

        if request.status_code != 200:
            log.error(request.text)
            raise Exception("Failed to add device %s into ONOS" % o.name)
        else:
            try:
                print request.json()
            except Exception:
                print request.text

    def delete_record(self, o):
        log.info("Deleting device", object=str(o), **o.tologdict())

        voltha = Helpers.get_voltha_info(o.volt_service)
        onos_voltha = Helpers.get_onos_voltha_info(o.volt_service)
        onos_voltha_basic_auth = HTTPBasicAuth(onos_voltha['user'], onos_voltha['pass'])

        if not o.device_id:
            log.error("Device %s has no device_id" % o.name)
        else:
            # Remove the device from ONOS
            request = requests.delete("%s:%d/onos/v1/network/configuration/devices/%s" % (onos_voltha['url'], onos_voltha['port'], o.of_id), auth=onos_voltha_basic_auth)

            if request.status_code != 200:
                log.error("Failed to remove device from ONOS: %s - %s" % (o.name, o.of_id), rest_responese=request.text, rest_status_code=request.status_code)
                raise Exception("Failed to remove device in ONOS")

            # Disable the device
            request = requests.post("%s:%d/api/v1/devices/%s/disable" % (voltha['url'], voltha['port'], o.device_id))

            if request.status_code != 200:
                log.error("Failed to disable device in VOLTHA: %s - %s" % (o.name, o.device_id), rest_responese=request.text, rest_status_code=request.status_code)
                raise Exception("Failed to disable device in VOLTHA")

            # Delete the device
            request = requests.delete("%s:%d/api/v1/devices/%s/delete" % (voltha['url'], voltha['port'], o.device_id))

            if request.status_code != 200:
                log.error("Failed to delete device in VOLTHA: %s - %s" % (o.name, o.device_id), rest_responese=request.text, rest_status_code=request.status_code)
                raise Exception("Failed to delete device in VOLTHA")
