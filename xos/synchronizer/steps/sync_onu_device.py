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
from synchronizers.new_base.modelaccessor import ONUDevice, model_accessor
from synchronizers.new_base.syncstep import SyncStep
from xosconfig import Config

log = create_logger(Config().get("logging"))

class SyncONUDevice(SyncStep):
    provides = [ONUDevice]

    observes = ONUDevice

    def disable_onu(self, o):
        volt_service = o.pon_port.olt_device.volt_service
        voltha = Helpers.get_voltha_info(volt_service)

        log.info("Disabling device %s in voltha" % o.device_id)
        request = requests.post("%s:%d/api/v1/devices/%s/disable" % (voltha['url'], voltha['port'], o.device_id))

        if request.status_code != 200:
            raise Exception("Failed to disable ONU device %s: %s" % (o.serial_number, request.text))

    def enable_onu(self, o):
        volt_service = o.pon_port.olt_device.volt_service
        voltha = Helpers.get_voltha_info(volt_service)

        log.info("Enabling device %s in voltha" % o.device_id)
        request = requests.post("%s:%d/api/v1/devices/%s/enable" % (voltha['url'], voltha['port'], o.device_id))

        if request.status_code != 200:
            raise Exception("Failed to enable ONU device %s: %s" % (o.serial_number, request.text))

    def sync_record(self, o):

        if o.admin_state == "DISABLED":
            self.disable_onu(o)
        if o.admin_state == "ENABLED":
            self.enable_onu(o)