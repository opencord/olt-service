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

from synchronizers.new_base.pullstep import PullStep
from synchronizers.new_base.modelaccessor import model_accessor, ONUDevice, VOLTService, OLTDevice

from xosconfig import Config
from multistructlog import create_logger

import requests
from requests import ConnectionError
from requests.models import InvalidURL

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import Helpers

log = create_logger(Config().get('logging'))

class ONUDevicePullStep(PullStep):
    def __init__(self):
        super(ONUDevicePullStep, self).__init__(observed_model=ONUDevice)

    def pull_records(self):
        log.info("pulling ONU devices from VOLTHA")

        try:
            self.volt_service = VOLTService.objects.all()[0]
        except IndexError:
            log.warn('VOLTService not found')
            return

        voltha_url = Helpers.get_voltha_info(self.volt_service)['url']
        voltha_port = Helpers.get_voltha_info(self.volt_service)['port']

        try:
            r = requests.get("%s:%s/api/v1/devices" % (voltha_url, voltha_port))

            if r.status_code != 200:
                log.info("It was not possible to fetch devices from VOLTHA")

            # keeping only ONUs
            devices = [d for d in r.json()["items"] if "onu" in d["type"]]

            log.debug("received devices", onus=devices)

            # TODO
            # [ ] delete ONUS as ONUDevice.objects.all() - updated OLTs

            if r.status_code != 200:
                log.info("It was not possible to fetch devices from VOLTHA")

            onus_in_voltha = self.create_or_update_onus(devices)

        except ConnectionError, e:
            log.warn("It was not possible to connect to VOLTHA", reason=e)
            return
        except InvalidURL, e:
            log.warn("VOLTHA url is invalid, is it configured in the VOLTService?", reason=e)
            return

    def create_or_update_onus(self, onus):

        updated_onus = []

        for onu in onus:
            try:

                model = ONUDevice.objects.filter(serial_number=onu["serial_number"])[0]
                log.debug("ONUDevice already exists, updating it", serial_number=onu["serial_number"])

                if model.enacted < model.updated:
                    log.info("Skipping pull on ONUDevice %s as enacted < updated" % model.name, name=model.name, id=model.id, enacted=model.enacted, updated=model.updated)
                    return

            except IndexError:
                model = ONUDevice()
                model.serial_number = onu["serial_number"]

                log.debug("ONUDevice is new, creating it", serial_number=onu["serial_number"])

            # Adding feedback state to the device
            model.vendor = onu["vendor"]
            model.device_type = onu["type"]
            model.device_id = onu["id"]

            model.admin_state = onu["admin_state"]
            model.oper_status = onu["oper_status"]
            model.connect_status = onu["connect_status"]

            olt = OLTDevice.objects.get(device_id=onu["proxy_address"]["device_id"])

            model.olt_device = olt
            model.olt_device_id = olt.id

            model.save()

            updated_onus.append(model)

        return updated_onus






