
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
from synchronizers.new_base.eventstep import EventStep
from synchronizers.new_base.modelaccessor import VOLTService, ONUDevice, Service, model_accessor

# from xos.exceptions import XOSValidationError


# Manually send the event

# import json
# from kafka import KafkaProducer

# event = json.dumps({
#     'status': 'activate',
#     'serial_number': 'BRCM1234',
#     'uni_port_of_id': 'of:00100101',
#     'of_dpid': 'of:109299321'
# })
# producer = KafkaProducer(bootstrap_servers="cord-kafka-kafka")
# producer.send("onu.events", event)
# producer.flush()


class ONUEventStep(EventStep):
    topics = ["onu.events"]
    technology = "kafka"

    def __init__(self, *args, **kwargs):
        super(ONUEventStep, self).__init__(*args, **kwargs)

    def get_oss_service(self, onu_serial_number):
        try:
            onu = ONUDevice.objects.get(serial_number=onu_serial_number)
        except IndexError as e:
            raise Exception("No ONUDevice with serial_number %s is present in XOS" % onu_serial_number)

        volt_service = onu.pon_port.olt_device.volt_service
        service = Service.objects.get(id=volt_service.id)
        osses = [s for s in service.provider_services if s.kind.lower() == "oss"]

        if len(osses) > 1:
            self.log.warn("More than one OSS found for %s" % volt_service.name)
        try:
            return osses[0].leaf_model
        except IndexError as e:
            return None

    def handle_onu_activate_event(self, event):
        oss = self.get_oss_service(event["serial_number"])

        if not oss:
            self.log.info("Not processing events as no OSS service is present (is it a provider of vOLT?")
        else:
            try:
                oss.validate_onu(event)
            except Exception, e:
                self.log.exception("Failing to validate ONU in OSS Service %s" % oss.name)
                raise e

    def process_event(self, event):
        value = json.loads(event.value)
        self.log.info("onu.events: received event", value=value)

        if value["status"] == "activate":
            self.log.info("onu.events: activate onu", value=value)
            self.handle_onu_activate_event(value)

