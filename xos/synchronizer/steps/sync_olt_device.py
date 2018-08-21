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

from time import sleep

import requests
from multistructlog import create_logger
from requests.auth import HTTPBasicAuth
from synchronizers.new_base.syncstep import SyncStep, DeferredException
from synchronizers.new_base.modelaccessor import OLTDevice, model_accessor
from xosconfig import Config

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import Helpers

log = create_logger(Config().get('logging'))

class SyncOLTDevice(SyncStep):
    provides = [OLTDevice]
    observes = OLTDevice

    max_attempt = 120  # we give 10 minutes to the OLT to activate

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

        raise Exception("Can't find a logical_device for OLT device id: %s" % o.device_id)

    def pre_provision_olt_device(self, model):
        log.info("Pre-provisioning OLT device in VOLTHA", object=str(model), **model.tologdict())

        voltha = Helpers.get_voltha_info(model.volt_service)

        data = {
            "type": model.device_type
        }

        if hasattr(model, "host") and hasattr(model, "port"):
            data["host_and_port"] = "%s:%s" % (model.host, model.port)
        elif hasattr(model, "mac_address"):
            data["mac_address"] = model.mac_address

        log.info("Pushing OLT to Voltha", data=data)

        request = requests.post("%s:%d/api/v1/devices" % (voltha['url'], voltha['port']), json=data)

        if request.status_code != 200:
            raise Exception("Failed to add OLT device: %s" % request.text)

        log.info("Add device response", text=request.text)

        res = request.json()

        log.info("Add device json res", res=res)

        if not res['id']:
            raise Exception(
                'VOLTHA Device Id is empty. This probably means that the OLT device is already provisioned in VOLTHA')
        else:
            model.device_id = res['id'];

        return model

    def activate_olt(self, model):

        attempted = 0

        voltha = Helpers.get_voltha_info(model.volt_service)

        # Enable device
        request = requests.post("%s:%d/api/v1/devices/%s/enable" % (voltha['url'], voltha['port'], model.device_id))

        if request.status_code != 200:
            raise Exception("Failed to enable OLT device: %s" % request.text)

        model.backend_status = "Waiting for device to be activated"
        model.save(always_update_timestamp=False) # we don't want to kickoff a new loop

        # Read state
        request = requests.get("%s:%d/api/v1/devices/%s" % (voltha['url'], voltha['port'], model.device_id)).json()
        while request['oper_status'] == "ACTIVATING" and attempted < self.max_attempt:
            log.info("Waiting for OLT device %s (%s) to activate" % (model.name, model.device_id))
            sleep(5)
            request = requests.get("%s:%d/api/v1/devices/%s" % (voltha['url'], voltha['port'], model.device_id)).json()
            attempted = attempted + 1


        model.admin_state = request['admin_state']
        model.oper_status = request['oper_status']

        if model.oper_status != "ACTIVE":
            raise Exception("It was not possible to activate OLTDevice with id %s" % model.id)

        # Find the of_id of the device
        model = self.get_ids_from_logical_device(model)
        model.save()

        return model

    def sync_record(self, model):
        log.info("Synching device", object=str(model), **model.tologdict())

        # If the device has feedback_state is already present in voltha
        if not model.device_id and not model.admin_state and not model.oper_status and not model.of_id:
            log.info("Pushing OLT device to VOLTHA", object=str(model), **model.tologdict())
            model = self.pre_provision_olt_device(model)
            self.activate_olt(model)
        elif model.oper_status != "ACTIVE":
            raise Exception("It was not possible to activate OLTDevice with id %s" % model.id)
        else:
            log.info("OLT device already exists in VOLTHA", object=str(model), **model.tologdict())

    def delete_record(self, model):
        log.info("Deleting OLT device", object=str(model), **model.tologdict())

        voltha = Helpers.get_voltha_info(model.volt_service)

        if not model.device_id:
            log.error("OLTDevice %s has no device_id" % model.name)
        else:
            # Disable the OLT device
            request = requests.post("%s:%d/api/v1/devices/%s/disable" % (voltha['url'], voltha['port'], model.device_id))

            if request.status_code != 200:
                log.error("Failed to disable OLT device in VOLTHA: %s - %s" % (model.name, model.device_id), rest_response=request.text, rest_status_code=request.status_code)
                raise Exception("Failed to disable OLT device in VOLTHA")

            # Delete the OLT device
            request = requests.delete("%s:%d/api/v1/devices/%s/delete" % (voltha['url'], voltha['port'], model.device_id))

            if request.status_code != 200:
                log.error("Failed to delete OLT device from VOLTHA: %s - %s" % (model.name, model.device_id), rest_response=request.text, rest_status_code=request.status_code)
                raise Exception("Failed to delete OLT device from VOLTHA")
