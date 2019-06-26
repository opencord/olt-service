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
from xossynchronizer.steps.syncstep import SyncStep, DeferredException
from xossynchronizer.modelaccessor import OLTDevice, TechnologyProfile, model_accessor
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

        # TODO(smbaker): Potential partial failure. If device is created in Voltha but synchronizer crashes before the
        # model is saved, then synchronizer will continue to try to preprovision and fail due to preexisting
        # device.

        if not res['id']:
            raise Exception(
                'VOLTHA Device Id is empty. This probably means that the OLT device is already provisioned in VOLTHA')
        else:
            model.device_id = res['id']

            # Only update the serial number if it is not already populated. See comments in similar code in the
            # pull step. Let the pull step handle emitting any error message if the serial numbers differ.
            if res['serial_number'] and (not model.serial_number):
                log.info("Sync step learned olt serial number from voltha",
                         model_serial_number=model.serial_number,
                         voltha_serial_number=res['serial_number'],
                         olt_id=model.id)
                model.serial_number = res['serial_number']

            model.save_changed_fields()

    def activate_olt(self, model):

        attempted = 0

        voltha = Helpers.get_voltha_info(model.volt_service)

        # Enable device
        request = requests.post("%s:%d/api/v1/devices/%s/enable" % (voltha['url'], voltha['port'], model.device_id))

        if request.status_code != 200:
            raise Exception("Failed to enable OLT device: %s" % request.text)

        model.backend_status = "Waiting for device to be activated"
        model.save_changed_fields(always_update_timestamp=False) # we don't want to kickoff a new loop

        # Read state
        request = requests.get("%s:%d/api/v1/devices/%s" % (voltha['url'], voltha['port'], model.device_id)).json()
        while request['oper_status'] == "ACTIVATING" and attempted < self.max_attempt:
            log.info("Waiting for OLT device %s (%s) to activate" % (model.name, model.device_id))
            sleep(5)
            request = requests.get("%s:%d/api/v1/devices/%s" % (voltha['url'], voltha['port'], model.device_id)).json()
            attempted = attempted + 1

        model.oper_status = request['oper_status']

        # Only update the serial number if it is not already populated. See comments in similar code in the
        # pull step. Let the pull step handle emitting any error message if the serial numbers differ.
        if request['serial_number'] and (not model.serial_number):
            log.info("Sync step learned olt serial number from voltha",
                     model_serial_number=model.serial_number,
                     voltha_serial_number=request['serial_number'],
                     olt_id=model.id)
            model.serial_number = request['serial_number']

        if model.oper_status != "ACTIVE":
            raise Exception("It was not possible to activate OLTDevice with id %s" % model.id)

        # Find the of_id of the device
        self.get_ids_from_logical_device(model)
        model.save_changed_fields()

    def deactivate_olt(self, model):
        voltha = Helpers.get_voltha_info(model.volt_service)

        # Disable device
        request = requests.post("%s:%d/api/v1/devices/%s/disable" % (voltha['url'], voltha['port'], model.device_id))

        if request.status_code != 200:
            raise Exception("Failed to disable OLT device: %s" % request.text)

    def configure_onos(self, model):

        log.info("Adding OLT device in onos-voltha", object=str(model), **model.tologdict())

        onos_voltha = Helpers.get_onos_voltha_info(model.volt_service)
        onos_voltha_basic_auth = HTTPBasicAuth(onos_voltha['user'], onos_voltha['pass'])

        # Add device info to onos-voltha
        data = {
            "devices": {
                model.dp_id: {
                    "basic": {
                        "name": model.name
                    }
                }
            }
        }

        log.info("Calling ONOS", data=data)

        url = "%s:%d/onos/v1/network/configuration/" % (onos_voltha['url'], onos_voltha['port'])
        request = requests.post(url, json=data, auth=onos_voltha_basic_auth)

        if request.status_code != 200:
            log.error(request.text)
            raise Exception("Failed to add OLT device %s into ONOS" % model.name)
        else:
            try:
                print request.json()
            except Exception:
                print request.text

    def wait_for_tp(self, technology):
        """
        Check if a technology profile for this technology has been already pushed to ETCD,
        if not defer the OLT Provisioning.
        :param technology: string - the technology to check for a tech profile
        :return: True (or raises DeferredException)
        """
        try:
            tps = TechnologyProfile.objects.get(technology=technology, backend_code=1)
        except IndexError:
            raise DeferredException("Waiting for a TechnologyProfile (technology=%s) to be synchronized" % technology)

        return True

    def sync_record(self, model):
        log.info("Synching device", object=str(model), **model.tologdict())

        self.wait_for_tp(model.technology)

        if model.admin_state not in ["ENABLED", "DISABLED"]:
            raise Exception("OLT Device %s admin_state has invalid value %s" % (model.id, model.admin_state))

        # If the device has feedback_state is already present in voltha
        if not model.device_id and not model.oper_status and not model.of_id:
            log.info("Pushing OLT device to VOLTHA", object=str(model), **model.tologdict())
            self.pre_provision_olt_device(model)
            model.oper_status = "UNKNOWN" # fall-though to activate OLT
        else:
            log.info("OLT device already exists in VOLTHA", object=str(model), **model.tologdict())

        # Reconcile admin_state and oper_status, activating or deactivating the OLT as necessary.

        if model.oper_status != "ACTIVE" and model.admin_state == "ENABLED":
            self.activate_olt(model)
        elif model.oper_status == "ACTIVE" and model.admin_state == "DISABLED":
            self.deactivate_olt(model)

        if model.admin_state == "ENABLED":
            # If we were not able to reconcile ENABLE/ACTIVE, then throw an exception and do not proceed to onos
            # configuration.
            if model.oper_status != "ACTIVE":
                raise Exception("It was not possible to activate OLTDevice with id %s" % model.id)

            # At this point OLT is enabled and active. Configure ONOS.
            self.configure_onos(model)

    def delete_record(self, model):
        log.info("Deleting OLT device", object=str(model), **model.tologdict())

        voltha = Helpers.get_voltha_info(model.volt_service)

        if not model.device_id or model.backend_code == 2:
            # NOTE if the device was not synchronized, just remove it from the data model
            log.warning("OLTDevice %s has no device_id, it was never saved in VOLTHA" % model.name)
            return
        else:
            try:
                # Disable the OLT device
                request = requests.post("%s:%d/api/v1/devices/%s/disable" % (voltha['url'], voltha['port'], model.device_id))

                if request.status_code != 200:
                    log.error("Failed to disable OLT device in VOLTHA: %s - %s" % (model.name, model.device_id), rest_response=request.text, rest_status_code=request.status_code)
                    raise Exception("Failed to disable OLT device in VOLTHA")

                # NOTE [teo] wait some time after the disable to let VOLTHA doing its things
                i = 0
                for i in list(reversed(range(10))):
                    sleep(1)
                    log.info("Deleting the OLT in %s seconds" % i)

                # Delete the OLT device
                request = requests.delete("%s:%d/api/v1/devices/%s/delete" % (voltha['url'], voltha['port'], model.device_id))

                if request.status_code != 200:
                    log.error("Failed to delete OLT device from VOLTHA: %s - %s" % (model.name, model.device_id), rest_response=request.text, rest_status_code=request.status_code)
                    raise Exception("Failed to delete OLT device from VOLTHA")
            except requests.ConnectionError:
                log.warning("ConnectionError when contacting Voltha in OLT delete step", name=model.name, device_id=model.device_id)
