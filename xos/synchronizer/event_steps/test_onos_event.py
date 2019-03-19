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
import functools
from mock import patch, call, Mock, PropertyMock
import requests_mock

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

class TestOnosPortEvent(unittest.TestCase):

    def setUp(self):
        global DeferredException

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("olt-service", "volt.xproto"),])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from mock_modelaccessor import MockObjectList
        from onos_event import OnosPortEventStep

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.event_step = OnosPortEventStep

        self.volt_service = VOLTService(name="volt",
                                        id=1112,
                                        backend_code=1,
                                        backend_status="succeeded")

        self.oltdevice = OLTDevice(name="myolt",
                                   switch_datapath_id="of:0000000000000001",
                                   switch_port="1")

        self.log = Mock()

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_process_event_enable(self):
        with patch.object(OLTDevice.objects, "get_items") as olt_objects, \
             patch.object(OLTDevice, "save", autospec=True) as olt_save:
            olt_objects.return_value = [self.oltdevice]

            event_dict = {"deviceId": self.oltdevice.switch_datapath_id,
                          "portId": self.oltdevice.switch_port,
                          "enabled": True}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.oltdevice.link_status, "up")

    def test_process_event_disable(self):
        with patch.object(OLTDevice.objects, "get_items") as olt_objects, \
             patch.object(OLTDevice, "save", autospec=True) as olt_save:
            olt_objects.return_value = [self.oltdevice]

            event_dict = {"deviceId": self.oltdevice.switch_datapath_id,
                          "portId": self.oltdevice.switch_port,
                          "enabled": False}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.oltdevice.link_status, "down")

    def test_process_event_no_olt(self):
        with patch.object(OLTDevice.objects, "get_items") as olt_objects, \
             patch.object(OLTDevice, "save", autospec=True) as olt_save:
            olt_objects.return_value = [self.oltdevice]

            event_dict = {"deviceId": "doesnotexist",
                          "portId": self.oltdevice.switch_port,
                          "enabled": True}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            # should not have changed
            self.assertEqual(self.oltdevice.link_status, None)

if __name__ == '__main__':
    unittest.main()
