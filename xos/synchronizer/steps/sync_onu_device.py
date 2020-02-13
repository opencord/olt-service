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

from multistructlog import create_logger
from xossynchronizer.modelaccessor import ONUDevice
from xossynchronizer.steps.syncstep import SyncStep
from xosconfig import Config

import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from voltha_client import get_voltha_client

log = create_logger(Config().get("logging"))


class SyncONUDevice(SyncStep):
    provides = [ONUDevice]

    observes = ONUDevice

    def disable_onu(self, o):
        volt_service = o.pon_port.olt_device.volt_service

        log.info("Disabling device %s in voltha" % o.device_id)
        try:
            get_voltha_client(volt_service).disable_device(o.device_id)
        except Exception as e:
            e.message = "[Enable ONU] " + e.message
            log.error(e.message)
            raise e

    def enable_onu(self, o):
        volt_service = o.pon_port.olt_device.volt_service

        log.info("Enabling device %s in voltha" % o.device_id)
        try:
            get_voltha_client(volt_service).enable_device(o.device_id)
        except Exception as e:
            e.message = "[Enable ONU] " + e.message
            log.error(e.message)
            raise e

    def sync_record(self, o):
        if o.admin_state in ["DISABLED", "ADMIN_DISABLED"]:
            self.disable_onu(o)
        if o.admin_state == "ENABLED":
            self.enable_onu(o)
