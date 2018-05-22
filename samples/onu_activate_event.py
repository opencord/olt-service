# Manually send the event

import json
from kafka import KafkaProducer

event = json.dumps({
    'status': 'activate',
    'serial_number': 'BRCM1234',
    'uni_port_id': 16,
    'of_dpid': 'of:109299321'
})
producer = KafkaProducer(bootstrap_servers="cord-kafka-kafka")
producer.send("onu.events", event)
producer.flush()