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
from synchronizers.new_base.modelaccessor import model_accessor, OLTDevice, VOLTService

from xosconfig import Config
from multistructlog import create_logger

import requests
from requests import ConnectionError
from requests.models import InvalidURL

log = create_logger(Config().get('logging'))

class OLTDevicePullStep(PullStep):
    def __init__(self):
        super(OLTDevicePullStep, self).__init__(observed_model=OLTDevice)

    # NOTE move helpers where they can be loaded by multiple modules?
    @staticmethod
    def format_url(url):
        if 'http' in url:
            return url
        else:
            return 'http://%s' % url

    @staticmethod
    def get_voltha_info(olt_service):
        return {
            'url': OLTDevicePullStep.format_url(olt_service.voltha_url),
            'user': olt_service.voltha_user,
            'pass': olt_service.voltha_pass
        }

    @staticmethod
    def datapath_id_to_hex(id):
        if isinstance(id, basestring):
            id = int(id)
        return "{0:0{1}x}".format(id, 16)

    @staticmethod
    def get_ids_from_logical_device(o):
        voltha_url = OLTDevicePullStep.get_voltha_info(o.volt_service)['url']

        r = requests.get(voltha_url + "/api/v1/logical_devices")

        if r.status_code != 200:
            raise Exception("Failed to retrieve logical devices from VOLTHA: %s" % r.text)

        res = r.json()

        for ld in res["items"]:
            if ld["root_device_id"] == o.device_id:
                o.of_id = ld["id"]
                o.dp_id = "of:" + OLTDevicePullStep.datapath_id_to_hex(ld["datapath_id"])  # convert to hex
                return o

        raise Exception("Can't find a logical device for device id: %s" % o.device_id)
    # end note

    def pull_records(self):
        log.info("pulling OLT devices from VOLTHA")

        try:
            self.volt_service = VOLTService.objects.all()[0]
        except IndexError:
            log.warn('VOLTService not found')
            return

        voltha_url = OLTDevicePullStep.get_voltha_info(self.volt_service)['url']

        try:
            devices = []
            r = requests.get(voltha_url + "/api/v1/devices")

            if r.status_code != 200:
                log.info("It was not possible to fetch devices from VOLTHA")

            # keeping only OLTs
            devices = [d for d in r.json()["items"] if "olt" in d["type"]]

            log.debug("received devices", olts=devices)

            # TODO
            # [X] for each device
            # [X] check if exists, if not save it
            # [X] if exists and enacted > updated it has already been sync'ed
            # [X] keep track of the updated OLTs
            # delete OLTS as OLTDevice.objects.all() - updated OLTs

            if r.status_code != 200:
                log.info("It was not possible to fetch devices from VOLTHA")

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
                    return

            except IndexError:
                model = OLTDevice()
                model.device_type = olt["type"]

                if olt["type"] == "simulated_olt":
                    model.host = "172.17.0.1"
                    model.port = 50060

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

            updated_olts.append(model)

        return updated_olts






