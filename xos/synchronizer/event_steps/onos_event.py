
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


import datetime
import json
import time
from xossynchronizer.event_steps.eventstep import EventStep
from xosconfig import Config
from xoskafka import XOSKafkaProducer
from multistructlog import create_logger

log = create_logger(Config().get('logging'))


class OnosPortEventStep(EventStep):
    topics = ["onos.events.port"]
    technology = "kafka"

    def __init__(self, *args, **kwargs):
        super(OnosPortEventStep, self).__init__(*args, **kwargs)

    def subscriber_olt_closure(self, olt):
        subscribers = []
        for pon_port in olt.pon_ports.all():
            for onu_device in pon_port.onu_devices.all():
                for si in onu_device.volt_service_instances.all():
                    for subscriber in si.westbound_service_instances:
                        subscribers.append(subscriber)
        return subscribers

    def send_alarm(self, olt, value):
        timestamp = time.mktime(datetime.datetime.strptime(value["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
        state = "RAISED" if olt.link_status == "down" else "CLEARED"

        # Hypothetically, a maximum of 64 subscribers per pon port, 16 pon ports, and 32 characters
        # per subscriber name = 32KB of subscriber names in the event.
        subscribers = self.subscriber_olt_closure(olt)
        subscribers = [x.name for x in subscribers]

        alarm = {"category": "OLT",
                 "reported_ts": time.time(),
                 "raised_ts": timestamp,
                 "state": state,
                 "alarm_type_name": "OLT.PORT_LOS",
                 "severity": "MAJOR",
                 "resource_id": olt.device_id,
                 "logical_device_id": olt.dp_id,
                 "context": {"affected_subscribers": subscribers,
                             "switch_datapath_id": olt.switch_datapath_id,
                             "switch_port": olt.switch_port,
                             "oltdevice.name": olt.name},
                 "type": "COMMUNICATION",
                 "id": "xos.voltservice.%s.OLT_PORT_LOS" % olt.device_id,
                 "description": "xos.voltservice.%s - OLT PORT LOS Alarm -"
                                " OLT_PORT_LOS - %s" % (olt.device_id, state)}

        topic = "xos.alarms.olt-service"
        key = olt.device_id
        value = json.dumps(alarm, default=lambda o: repr(o))

        XOSKafkaProducer.produce(topic, key, value)

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
            self.send_alarm(olt, value)
