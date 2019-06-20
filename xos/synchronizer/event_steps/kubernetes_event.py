
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


import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xossynchronizer.event_steps.eventstep import EventStep
from xossynchronizer.modelaccessor import VOLTService, VOLTServiceInstance, Service
from xosconfig import Config
from multistructlog import create_logger
from helpers import Helpers

log = create_logger(Config().get('logging'))

class KubernetesPodDetailsEventStep(EventStep):
    topics = ["xos.kubernetes.pod-details"]
    technology = "kafka"

    def __init__(self, *args, **kwargs):
        super(KubernetesPodDetailsEventStep, self).__init__(*args, **kwargs)

    def process_event(self, event):
        value = json.loads(event.value)

        if (value.get("status") != "created"):
            return

        if "labels" not in value:
            return

        xos_service = value["labels"].get("xos_service")
        if not xos_service:
            return

        for service in VOLTService.objects.all():
            onos = Helpers.get_onos_service_name(service)
            # NOTE do we really need to dynamically fetch the ONOS name?
            if (onos.lower() != xos_service.lower()):
                continue

            for service_instance in service.service_instances.all():
                log.info("Dirtying VOLTServiceInstance", service_instance=service_instance)
                service_instance.backend_code=0
                service_instance.backend_status="resynchronize due to kubernetes event"
                service_instance.save(update_fields=["updated", "backend_code", "backend_status"], always_update_timestamp=True)
