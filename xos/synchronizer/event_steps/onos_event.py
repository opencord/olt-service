
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
from xossynchronizer.event_steps.eventstep import EventStep
from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))


class OnosPortEventStep(EventStep):
    topics = ["onos.events.port"]
    technology = "kafka"

    def __init__(self, *args, **kwargs):
        super(OnosPortEventStep, self).__init__(*args, **kwargs)

    def process_event(self, event):
        log.info("Received ONOS Port Event", kafka_event=event)

        value = json.loads(event.value)

        olt = self.model_accessor.OLTDevice.objects.filter(switch_datapath_id=value["deviceId"],
                                                           switch_port=value["portId"])
        if not olt:
            log.info("Onos port event not for a known olt", deviceId=value["deviceId"], portId=value["portId"])
            return

        olt = olt[0]

        link_status = "up" if value["enabled"] else "down"
        if link_status != olt.link_status:
            olt.link_status = link_status
            olt.save_changed_fields()
