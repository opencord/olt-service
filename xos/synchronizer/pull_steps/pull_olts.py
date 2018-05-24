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
from synchronizers.new_base.modelaccessor import model_accessor, OLTDevice, VOLTService, PONPort, NNIPort

from xosconfig import Config
from multistructlog import create_logger

import requests
from requests import ConnectionError
from requests.models import InvalidURL

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import Helpers

log = create_logger(Config().get('logging'))

class OLTDevicePullStep(PullStep):
    def __init__(self):
        super(OLTDevicePullStep, self).__init__(observed_model=OLTDevice)

    @staticmethod
    def get_ids_from_logical_device(o):
        voltha_url = Helpers.get_voltha_info(o.volt_service)['url']
        voltha_port = Helpers.get_voltha_info(o.volt_service)['port']

        r = requests.get("%s:%s/api/v1/logical_devices" % (voltha_url, voltha_port))

        if r.status_code != 200:
            raise Exception("Failed to retrieve logical devices from VOLTHA: %s" % r.text)

        res = r.json()

        for ld in res["items"]:
            if ld["root_device_id"] == o.device_id:
                o.of_id = ld["id"]
                o.dp_id = "of:" + Helpers.datapath_id_to_hex(ld["datapath_id"])  # convert to hex
                return o

        raise Exception("Can't find a logical device for device id: %s" % o.device_id)

    def pull_records(self):
        log.info("pulling OLT devices from VOLTHA")

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

            # keeping only OLTs
            devices = [d for d in r.json()["items"] if "olt" in d["type"]]

            log.debug("received devices", olts=devices)

            # TODO
            # [ ] delete OLTS as OLTDevice.objects.all() - updated OLTs

            olts_in_voltha = self.create_or_update_olts(devices)

        except ConnectionError, e:
            log.warn("It was not possible to connect to VOLTHA", reason=e)
            return
        except InvalidURL, e:
            log.warn("VOLTHA url is invalid, is it configured in the VOLTService?", reason=e)
            return

    def create_or_update_olts(self, olts):

        updated_olts = []

        for olt in olts:
            try:
                if olt["type"] == "simulated_olt":
                    [host, port] = ["172.17.0.1", "50060"]
                else:
                    [host, port] = olt["host_and_port"].split(":")
                model = OLTDevice.objects.filter(device_type=olt["type"], host=host, port=port)[0]

                log.debug("OLTDevice already exists, updating it", device_type=olt["type"], host=host, port=port)

                if model.enacted < model.updated:
                    log.info("Skipping pull on OLTDevice %s as enacted < updated" % model.name, name=model.name, id=model.id, enacted=model.enacted, updated=model.updated)
                    # if we are not updating the device we still need to pull ports
                    self.fetch_olt_ports(model)
                    return

            except IndexError:
                model = OLTDevice()
                model.device_type = olt["type"]

                if olt["type"] == "simulated_olt":
                    model.host = "172.17.0.1"
                    model.port = 50060
                else:
                    [host, port] = olt["host_and_port"].split(":")
                    model.host = host
                    model.port = int(port)

                log.debug("OLTDevice is new, creating it", device_type=olt["type"], host=host, port=port)

            # Adding feedback state to the device
            model.device_id = olt["id"]
            model.admin_state = olt["admin_state"]
            model.oper_status = olt["oper_status"]

            model.volt_service = self.volt_service
            model.volt_service_id = self.volt_service.id

            # get logical device
            OLTDevicePullStep.get_ids_from_logical_device(model)

            model.save()

            self.fetch_olt_ports(model)

            updated_olts.append(model)

        return updated_olts

    def fetch_olt_ports(self, olt):
        voltha_url = Helpers.get_voltha_info(self.volt_service)['url']
        voltha_port = Helpers.get_voltha_info(self.volt_service)['port']

        try:
            r = requests.get("%s:%s/api/v1/devices/%s/ports" % (voltha_url, voltha_port, olt.device_id))

            if r.status_code != 200:
                log.info("It was not possible to fetch ports from VOLTHA for device %s" % olt.device_id)

            ports = r.json()['items']

            log.debug("received ports", ports=ports, olt=olt.device_id)

            self.create_or_update_ports(ports, olt)

        except ConnectionError, e:
            log.warn("It was not possible to connect to VOLTHA", reason=e)
            return
        except InvalidURL, e:
            log.warn("VOLTHA url is invalid, is it configured in the VOLTService?", reason=e)
            return
        return

    def create_or_update_ports(self, ports, olt):
        nni_ports = [p for p in ports if "ETHERNET_NNI" in p["type"]]
        pon_ports = [p for p in ports if "PON_OLT" in p["type"]]

        self.create_or_update_nni_port(nni_ports, olt)
        self.create_or_update_pon_port(pon_ports, olt)

    def create_or_update_pon_port(self, pon_ports, olt):

        update_ports = []

        for port in pon_ports:
            try:
                model = PONPort.objects.filter(port_no=port["port_no"], olt_device_id=olt.id)[0]
                log.debug("PONPort is new, creating it", port_no=port["port_no"], olt_device_id=olt.id)
            except IndexError:
                model = PONPort()
                model.port_no = port["port_no"]
                model.olt_device_id = olt.id
                model.name = port["label"]
                log.debug("PONPort already exists, updating it", port_no=port["port_no"], olt_device_id=olt.id)

            model.admin_state = port["admin_state"]
            model.oper_status = port["oper_status"]
            model.save()
            update_ports.append(model)
        return update_ports

    def create_or_update_nni_port(self, nni_ports, olt):
        update_ports = []

        for port in nni_ports:
            try:
                model = NNIPort.objects.filter(port_no=port["port_no"], olt_device_id=olt.id)[0]
                model.xos_managed = False
                log.debug("NNIPort is new, creating it", port_no=port["port_no"], olt_device_id=olt.id)
            except IndexError:
                model = NNIPort()
                model.port_no = port["port_no"]
                model.olt_device_id = olt.id
                model.name = port["label"]
                model.xos_managed = False
                log.debug("NNIPort already exists, updating it", port_no=port["port_no"], olt_device_id=olt.id)

            model.admin_state = port["admin_state"]
            model.oper_status = port["oper_status"]
            model.save()
            update_ports.append(model)
        return update_ports





