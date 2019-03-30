
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

# Manually send the event

import json
from kafka import KafkaProducer

event = json.dumps({
    'status': 'activated',
    'serialNumber': 'BRCM1234',
    'portNumber': '16',
    'deviceId': 'of:109299321'
})
producer = KafkaProducer(bootstrap_servers="cord-kafka")
producer.send("onu.events", event)
producer.flush()
