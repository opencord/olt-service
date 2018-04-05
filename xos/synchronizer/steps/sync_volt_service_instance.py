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

from synchronizers.new_base.syncstep import SyncStep, DeferredException
from synchronizers.new_base.modelaccessor import model_accessor
from synchronizers.new_base.modelaccessor import VOLTService, VOLTServiceInstance, ServiceInstance, OLTDevice

from xosconfig import Config
from multistructlog import create_logger
import requests
from requests.auth import HTTPBasicAuth
from helpers import Helpers

log = create_logger(Config().get("logging"))

class SyncVOLTServiceInstance(SyncStep):
    provides = [VOLTServiceInstance]

    observes = VOLTServiceInstance

    def sync_record(self, o):

        volt_service = VOLTService.objects.get(id=o.owner_id)

        si = ServiceInstance.objects.get(id=o.id)

        log.info("sync'ing OLTServiceInstance", object=str(o), **o.tologdict())

        c_tag = si.get_westbound_service_instance_properties("c_tag")
        uni_port_id = si.get_westbound_service_instance_properties("uni_port_id")

        olt_device_name = si.get_westbound_service_instance_properties("olt_device")

        olt_device = OLTDevice.objects.get(name=olt_device_name)

        if not olt_device.dp_id:
            raise DeferredException("Waiting for OLTDevice %s to be synchronized" % olt_device.name)

        log.debug("Adding subscriber with info",
                 c_tag=c_tag,
                 uni_port_id=uni_port_id,
                 dp_id=olt_device.dp_id)

        # sending request to ONOS

        onos = Helpers.get_p_onos_info(volt_service)

        url = onos['url'] + "/onos/olt/oltapp/%s/%s/%s" % (olt_device.dp_id, uni_port_id, c_tag)

        log.info("sending request to P_ONOS", url=url)

        r = requests.post(url,auth=HTTPBasicAuth(onos['user'], onos['pass']))

        if r.status_code != 200:
            raise Exception("Failed to add subscriber in P_ONOS: %s" % r.text)

        log.info("P_ONOS response", res=r.text)