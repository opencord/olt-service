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

import unittest
import json
from mock import patch, Mock, MagicMock, ANY

import datetime
import os
import sys
import time

test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))


class TestOnosPortEvent(unittest.TestCase):

    def setUp(self):
        global DeferredException

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")

        # Mock the kafka producer
        self.mockxoskafka = MagicMock()
        modules = {
            'xoskafka': self.mockxoskafka,
            'xoskafka.XOSKafkaProducer': self.mockxoskafka.XOSKafkaProducer,
        }
        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("olt-service", "volt.xproto"),
                                              ("rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor)  # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)  # in case nose2 loaded it in a previous test

        from mock_modelaccessor import MockObjectList
        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        # necessary to reset XOSKafkaProducer's call_count
        import onos_event
        reload(onos_event)

        from onos_event import OnosPortEventStep, XOSKafkaProducer
        from onos_event import XOSKafkaProducer
        self.XOSKafkaProducer = XOSKafkaProducer

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.event_step = OnosPortEventStep

        self.volt_service = VOLTService(name="volt",
                                        id=1112,
                                        backend_code=1,
                                        backend_status="succeeded")

        self.oltdevice = OLTDevice(name="myolt",
                                   device_id="of:0000000000000001",
                                   switch_datapath_id="of:0000000000000001",
                                   switch_port="1")

        self.ponport = PONPort(olt_device = self.oltdevice)

        self.onudevice = ONUDevice(pon_port = self.ponport)

        self.subscriber = RCORDSubscriber(name="somesubscriber")
        self.voltsi = VOLTServiceInstance()

        # chain it all together
        self.oltdevice.pon_ports = MockObjectList([self.ponport])
        self.ponport.onu_devices = MockObjectList([self.onudevice])
        self.onudevice.volt_service_instances = MockObjectList([self.voltsi])
        self.voltsi.westbound_service_instances = [self.subscriber]

        self.log = Mock()

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_process_event_enable(self):
        with patch.object(OLTDevice.objects, "get_items") as olt_objects:
            olt_objects.return_value = [self.oltdevice]

            event_dict = {"timestamp":"2019-03-21T18:00:26.613Z",
                          "deviceId": self.oltdevice.switch_datapath_id,
                          "portId": self.oltdevice.switch_port,
                          "enabled": True}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.oltdevice.link_status, "up")

    def test_process_event_disable(self):
        with patch.object(OLTDevice.objects, "get_items") as olt_objects:
            olt_objects.return_value = [self.oltdevice]

            event_dict = {"timestamp":"2019-03-21T18:00:26.613Z",
                          "deviceId": self.oltdevice.switch_datapath_id,
                          "portId": self.oltdevice.switch_port,
                          "enabled": False}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.oltdevice.link_status, "down")

    def test_process_event_no_olt(self):
        with patch.object(OLTDevice.objects, "get_items") as olt_objects:
            olt_objects.return_value = [self.oltdevice]

            event_dict = {"timestamp":"2019-03-21T18:00:26.613Z",
                          "deviceId": "doesnotexist",
                          "portId": self.oltdevice.switch_port,
                          "enabled": True}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            # should not have changed
            self.assertEqual(self.oltdevice.link_status, None)

    def test_send_alarm(self):
        self.oltdevice.link_status = "down"
        value = {"timestamp":"2019-03-21T18:00:26.613Z",
                 "deviceId":"of:0000000000000001",
                 "portId":"2",
                 "enabled":False,
                 "speed":10000,
                 "type":"COPPER"}

        step = self.event_step(model_accessor=self.model_accessor, log=self.log)
        step.send_alarm(self.oltdevice, value)

        self.assertEqual(self.XOSKafkaProducer.produce.call_count, 1)
        topic = self.XOSKafkaProducer.produce.call_args[0][0]
        key = self.XOSKafkaProducer.produce.call_args[0][1]
        event = json.loads(self.XOSKafkaProducer.produce.call_args[0][2])

        self.assertEqual(topic, "xos.alarms.olt-service")
        self.assertEqual(key, "of:0000000000000001")

        raised_ts = time.mktime(datetime.datetime.strptime(value["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())

        self.maxDiff = None

        expected_alarm = {
                 u"category": u"OLT",
                 u"reported_ts": ANY,
                 u"raised_ts": raised_ts,
                 u"state": u"RAISED",
                 u"alarm_type_name": u"OLT.PORT_LOS",
                 u"severity": u"MAJOR",
                 u"resource_id": unicode(self.oltdevice.device_id),
                 u"logical_device_id": self.oltdevice.dp_id,
                 u"context": {u'affected_subscribers': [u'somesubscriber'],
                              u"switch_datapath_id": "of:0000000000000001",
                              u"switch_port": "1",
                              u"oltdevice.name": "myolt"},
                 u"type": u"COMMUNICATION",
                 u"id": u"xos.voltservice.%s.OLT_PORT_LOS" % self.oltdevice.device_id,
                 u"description": u"xos.voltservice.%s - OLT PORT LOS Alarm - OLT_PORT_LOS - RAISED" % self.oltdevice.device_id}

        self.assertDictEqual(expected_alarm, event)

    def test_clear_alarm(self):
        self.oltdevice.link_status = "up"
        value = {"timestamp":"2019-03-21T18:00:26.613Z",
                 "deviceId":"of:0000000000000001",
                 "portId":"2",
                 "enabled":True,
                 "speed":10000,
                 "type":"COPPER"}

        step = self.event_step(model_accessor=self.model_accessor, log=self.log)
        step.send_alarm(self.oltdevice, value)

        self.assertEqual(self.XOSKafkaProducer.produce.call_count, 1)
        topic = self.XOSKafkaProducer.produce.call_args[0][0]
        key = self.XOSKafkaProducer.produce.call_args[0][1]
        event = json.loads(self.XOSKafkaProducer.produce.call_args[0][2])

        self.assertEqual(topic, "xos.alarms.olt-service")
        self.assertEqual(key, "of:0000000000000001")

        raised_ts = time.mktime(datetime.datetime.strptime(value["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())

        self.maxDiff = None

        expected_alarm = {
                 u"category": u"OLT",
                 u"reported_ts": ANY,
                 u"raised_ts": raised_ts,
                 u"state": u"CLEARED",
                 u"alarm_type_name": u"OLT.PORT_LOS",
                 u"severity": u"MAJOR",
                 u"resource_id": unicode(self.oltdevice.device_id),
                 u"logical_device_id": self.oltdevice.dp_id,
                 u"context": {u'affected_subscribers': [u'somesubscriber'],
                              u"switch_datapath_id": "of:0000000000000001",
                              u"switch_port": "1",
                              u"oltdevice.name": "myolt"},
                 u"type": u"COMMUNICATION",
                 u"id": u"xos.voltservice.%s.OLT_PORT_LOS" % self.oltdevice.device_id,
                 u"description": u"xos.voltservice.%s - OLT PORT LOS Alarm - OLT_PORT_LOS - CLEARED" % self.oltdevice.device_id}

        self.assertDictEqual(expected_alarm, event)


if __name__ == '__main__':
    unittest.main()
