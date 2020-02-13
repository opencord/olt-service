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

from voltha_protos.voltha_pb2 import ID
from voltha_protos.voltha_pb2_grpc import VolthaServiceStub
import grpc

from multistructlog import create_logger
from requests.auth import HTTPBasicAuth
from xossynchronizer.modelaccessor import ONUDevice, model_accessor
from xossynchronizer.steps.syncstep import SyncStep
from xosconfig import Config

log = create_logger(Config().get("logging"))

class SyncONUDevice(SyncStep):
    provides = [ONUDevice]

    observes = ONUDevice

    def disable_onu(self, o):
        volt_service = o.pon_port.olt_device.volt_service
        voltha = Helpers.get_voltha_info(volt_service)

        # FIXME: EXCEPTIONS??
        log.info("Disabling device %s in voltha" % o.device_id)
        with grpc.insecure_channel(voltha['url'] + ":" + str(voltha['port'])) as channel:
            stub = VolthaServiceStub(channel)
            onu_id = ID(id=o.device_id)
            stub.DisableDevice(onu_id)

    # FIXME: EXCEPTIONS??
    def enable_onu(self, o):
        volt_service = o.pon_port.olt_device.volt_service
        voltha = Helpers.get_voltha_info(volt_service)

        log.info("Enabling device %s in voltha" % o.device_id)
        with grpc.insecure_channel(voltha['url'] + ":" + str(voltha['port'])) as channel:
            stub = VolthaServiceStub(channel)
            onu_id = ID(id=o.device_id)
            stub.EnableDevice(onu_id)

    def sync_record(self, o):

        if o.admin_state in ["DISABLED", "ADMIN_DISABLED"]:
            self.disable_onu(o)
        if o.admin_state == "ENABLED":
            self.enable_onu(o)