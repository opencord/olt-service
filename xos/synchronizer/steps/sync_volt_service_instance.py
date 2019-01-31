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
from xossynchronizer.modelaccessor import VOLTService, VOLTServiceInstance, ServiceInstance, model_accessor
from xossynchronizer.steps.syncstep import SyncStep, DeferredException
from xosconfig import Config

log = create_logger(Config().get("logging"))

class SyncVOLTServiceInstance(SyncStep):
    provides = [VOLTServiceInstance]

    observes = VOLTServiceInstance

    def sync_record(self, o):

        if o.policy_code != 1:
            raise DeferredException("Waiting for ModelPolicy to complete")

        volt_service = VOLTService.objects.get(id=o.owner_id)

        log.info("Synching OLTServiceInstance", object=str(o), **o.tologdict())

        olt_device = o.onu_device.pon_port.olt_device

        try:
            # NOTE each ONU has only one UNI port!
            uni_port_id = o.onu_device.uni_ports.first().port_no
        except AttributeError:
            # This is because the ONUDevice is set by model_policy
            raise DeferredException("Waiting for ONUDevice %s " % olt_device.name)

        if not olt_device.dp_id:
            raise DeferredException("Waiting for OLTDevice %s to be synchronized" % olt_device.name)

        log.debug("Adding subscriber with info",
                 uni_port_id = uni_port_id,
                 dp_id = olt_device.dp_id
        )

        # Send request to ONOS
        onos_voltha = Helpers.get_onos_voltha_info(volt_service)
        onos_voltha_basic_auth = HTTPBasicAuth(onos_voltha['user'], onos_voltha['pass'])

        handle = "%s/%s" % (olt_device.dp_id, uni_port_id)

        full_url = "%s:%d/onos/olt/oltapp/%s" % (onos_voltha['url'], onos_voltha['port'], handle)

        log.info("Sending request to onos-voltha", url=full_url)

        request = requests.post(full_url, auth=onos_voltha_basic_auth)

        if request.status_code != 200:
            raise Exception("Failed to add subscriber in onos-voltha: %s" % request.text)

        o.backend_handle = handle
        o.save(update_fields=["backend_handle"])

        log.info("Added Subscriber in onos voltha", response=request.text)
    
    def delete_record(self, o):

        log.info("Removing OLTServiceInstance", object=str(o), **o.tologdict())

        volt_service = VOLTService.objects.get(id=o.owner_id)
        onos_voltha = Helpers.get_onos_voltha_info(volt_service)
        onos_voltha_basic_auth = HTTPBasicAuth(onos_voltha['user'], onos_voltha['pass'])

        full_url = "%s:%d/onos/olt/oltapp/%s" % (onos_voltha['url'], onos_voltha['port'], o.backend_handle)

        request = requests.delete(full_url, auth=onos_voltha_basic_auth)

        if request.status_code != 204:
            raise Exception("Failed to remove subscriber from onos-voltha: %s" % request.text)

        log.info("Removed Subscriber from onos voltha", response=request.text)