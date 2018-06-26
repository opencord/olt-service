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
from synchronizers.new_base.modelaccessor import VOLTService, VOLTServiceInstance, ServiceInstance, model_accessor
from synchronizers.new_base.syncstep import SyncStep, DeferredException
from xosconfig import Config

log = create_logger(Config().get("logging"))

class SyncVOLTServiceInstance(SyncStep):
    provides = [VOLTServiceInstance]

    observes = VOLTServiceInstance

    def sync_record(self, o):

        volt_service = VOLTService.objects.get(id=o.owner_id)

        si = ServiceInstance.objects.get(id=o.id)

        log.info("Synching OLTServiceInstance", object=str(o), **o.tologdict())

        c_tag = si.get_westbound_service_instance_properties("c_tag")

        olt_device = o.onu_device.pon_port.olt_device

        # NOTE each ONU has only one UNI port!
        uni_port_id = o.onu_device.uni_ports.first().port_no

        if not olt_device.dp_id:
            raise DeferredException("Waiting for OLTDevice %s to be synchronized" % olt_device.name)

        log.debug("Adding subscriber with info",
                 c_tag = c_tag,
                 uni_port_id = uni_port_id,
                 dp_id = olt_device.dp_id)

        # Send request to ONOS
        onos_voltha = Helpers.get_onos_voltha_info(volt_service)
        onos_voltha_basic_auth = HTTPBasicAuth(onos_voltha['user'], onos_voltha['pass'])

        full_url = "%s:%d/onos/olt/oltapp/%s/%s/%s" % (onos_voltha['url'], onos_voltha['port'], olt_device.dp_id, uni_port_id, c_tag)

        log.info("Sending request to onos-voltha", url=full_url)

        request = requests.post(full_url, auth=onos_voltha_basic_auth)

        if request.status_code != 200:
            raise Exception("Failed to add subscriber in onos-voltha: %s" % request.text)

        log.info("Added Subscriber in onos voltha", response=request.text)
    
    def delete_record(self, o):

        log.info("Removing OLTServiceInstance", object=str(o), **o.tologdict())

        volt_service = VOLTService.objects.get(id=o.owner_id)
        onos_voltha = Helpers.get_onos_voltha_info(volt_service)
        onos_voltha_basic_auth = HTTPBasicAuth(onos_voltha['user'], onos_voltha['pass'])

        olt_device = o.onu_device.pon_port.olt_device
        # NOTE each ONU has only one UNI port!
        uni_port_id = o.onu_device.uni_ports.first().port_no

        full_url = "%s:%d/onos/olt/oltapp/%s/%s" % (onos_voltha['url'], onos_voltha['port'], olt_device.dp_id, uni_port_id)

        request = requests.delete(full_url, auth=onos_voltha_basic_auth)

        if request.status_code != 204:
            raise Exception("Failed to remove subscriber from onos-voltha: %s" % request.text)

        log.info("Removed Subscriber from onos voltha", response=request.text)