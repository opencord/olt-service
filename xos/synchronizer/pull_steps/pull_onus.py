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

from xossynchronizer.pull_steps.pullstep import PullStep
from xossynchronizer.modelaccessor import model_accessor, ONUDevice, VOLTService, OLTDevice, PONPort, PONONUPort, UNIPort

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
    def __init__(self, model_accessor):
        super(ONUDevicePullStep, self).__init__(model_accessor=model_accessor, observed_model=ONUDevice)

    def pull_records(self):
        log.debug("pulling ONU devices from VOLTHA")

        try:
            self.volt_service = VOLTService.objects.all()[0]
        except IndexError:
            log.warn('VOLTService not found')
            return

        voltha_url = Helpers.get_voltha_info(self.volt_service)['url']
        voltha_port = Helpers.get_voltha_info(self.volt_service)['port']

        try:
            r = requests.get("%s:%s/api/v1/devices" % (voltha_url, voltha_port), timeout=1)

            if r.status_code != 200:
                log.warn("It was not possible to fetch devices from VOLTHA")

            # keeping only ONUs
            devices = [d for d in r.json()["items"] if "onu" in d["type"]]

            log.debug("received devices", onus=devices)

            # TODO
            # [ ] delete ONUS as ONUDevice.objects.all() - updated ONUs

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

            except IndexError:
                model = ONUDevice()
                model.serial_number = onu["serial_number"]
                model.admin_state = onu["admin_state"]

                log.debug("ONUDevice is new, creating it", serial_number=onu["serial_number"], admin_state=onu["admin_state"])

            try:
                olt = OLTDevice.objects.get(device_id=onu["parent_id"])
            except IndexError:
                log.warning("Unable to find olt for ONUDevice", serial_number=onu["serial_number"], olt_device_id=onu["parent_id"])
                continue

            try:
                pon_port = PONPort.objects.get(port_no=onu["parent_port_no"], olt_device_id=olt.id)
            except IndexError:
                log.warning("Unable to find pon_port for ONUDevice", serial_number=onu["serial_number"], olt_device_id=onu["parent_id"], port_no=onu["parent_port_no"])
                continue

            # Adding feedback state to the device
            model.vendor = onu["vendor"]
            model.device_type = onu["type"]
            model.device_id = onu["id"]

            model.oper_status = onu["oper_status"]
            model.connect_status = onu["connect_status"]
            model.reason = onu["reason"]
            model.xos_managed = False

            model.pon_port = pon_port
            model.pon_port_id = pon_port.id

            model.save_changed_fields()

            self.fetch_onu_ports(model)

            updated_onus.append(model)

        return updated_onus

    def fetch_onu_ports(self, onu):
        voltha_url = Helpers.get_voltha_info(self.volt_service)['url']
        voltha_port = Helpers.get_voltha_info(self.volt_service)['port']

        try:
            r = requests.get("%s:%s/api/v1/devices/%s/ports" % (voltha_url, voltha_port, onu.device_id), timeout=1)

            if r.status_code != 200:
                log.warn("It was not possible to fetch ports from VOLTHA for ONUDevice %s" % onu.device_id)

            ports = r.json()['items']

            log.debug("received ports", ports=ports, onu=onu.device_id)

            self.create_or_update_ports(ports, onu)

        except ConnectionError, e:
            log.warn("It was not possible to connect to VOLTHA", reason=e)
            return
        except InvalidURL, e:
            log.warn("VOLTHA url is invalid, is it configured in the VOLTService?", reason=e)
            return
        return

    def create_or_update_ports(self, ports, onu):
        uni_ports = [p for p in ports if "ETHERNET_UNI" in p["type"]]
        pon_onu_ports = [p for p in ports if "PON_ONU" in p["type"]]

        self.create_or_update_uni_port(uni_ports, onu)
        self.create_or_update_pon_onu_port(pon_onu_ports, onu)

    def get_onu_port_id(self, port, onu):
        # find the correct port id as represented in the logical_device
        logical_device_id = onu.pon_port.olt_device.of_id

        voltha_url = Helpers.get_voltha_info(self.volt_service)['url']
        voltha_port = Helpers.get_voltha_info(self.volt_service)['port']

        try:
            r = requests.get("%s:%s/api/v1/logical_devices/%s/ports" % (voltha_url, voltha_port, logical_device_id), timeout=1)

            if r.status_code != 200:
                log.warn("It was not possible to fetch ports from VOLTHA for logical_device %s" % logical_device_id)

            logical_ports = r.json()['items']
            log.debug("logical device ports for ONUDevice %s" % onu.device_id, logical_ports=logical_ports)

            ports = [p['ofp_port']['port_no'] for p in logical_ports if p['device_id'] == onu.device_id]
            # log.debug("Port_id for port %s on ONUDevice %s: %s" % (port['label'], onu.device_id, ports), logical_ports=logical_ports)
            # FIXME if this throws an error ONUs from other OTLs are not sync'ed
            return int(ports[0])

        except ConnectionError, e:
            log.warn("It was not possible to connect to VOLTHA", reason=e)
            return
        except InvalidURL, e:
            log.warn("VOLTHA url is invalid, is it configured in the VOLTService?", reason=e)
            return

    def create_or_update_uni_port(self, uni_ports, onu):
        update_ports = []

        for port in uni_ports:
            port_no = self.get_onu_port_id(port, onu)
            try:
                model = UNIPort.objects.filter(port_no=port_no, onu_device_id=onu.id)[0]
                log.debug("UNIPort already exists, updating it", port_no=port_no, onu_device_id=onu.id)
            except IndexError:
                model = UNIPort()
                model.port_no = port_no
                model.onu_device_id = onu.id
                model.name = port["label"]
                log.debug("UNIPort is new, creating it", port_no=port["port_no"], onu_device_id=onu.id)

            model.admin_state = port["admin_state"]
            model.oper_status = port["oper_status"]
            model.save_changed_fields()
            update_ports.append(model)
        return update_ports

    def create_or_update_pon_onu_port(self, pon_onu_ports, onu):
        update_ports = []

        for port in pon_onu_ports:
            try:
                model = PONONUPort.objects.filter(port_no=port["port_no"], onu_device_id=onu.id)[0]
                model.xos_managed = False
                log.debug("PONONUPort already exists, updating it", port_no=port["port_no"], onu_device_id=onu.id)
            except IndexError:
                model = PONONUPort()
                model.port_no = port["port_no"]
                model.onu_device_id = onu.id
                model.name = port["label"]
                model.xos_managed = False
                log.debug("PONONUPort is new, creating it", port_no=port["port_no"], onu_device_id=onu.id)

            model.admin_state = port["admin_state"]
            model.oper_status = port["oper_status"]
            model.save_changed_fields()
            update_ports.append(model)
        return update_ports
