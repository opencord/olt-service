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
from mock import patch, call, Mock, PropertyMock
import requests_mock

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

class TestSyncVOLTServiceInstance(unittest.TestCase):
    def setUp(self):

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("olt-service", "volt.xproto"),
                                                ("vsg", "vsg.xproto"),
                                                ("../profiles/rcord", "rcord.xproto"),])

        import xossynchronizer.modelaccessor
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from xossynchronizer.steps.syncstep import DeferredException
        from sync_onu_device import SyncONUDevice, model_accessor

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = SyncONUDevice

        volt_service = Mock()
        volt_service.voltha_url = "voltha_url"
        volt_service.voltha_port = 1234
        volt_service.voltha_user = "voltha_user"
        volt_service.voltha_pass = "voltha_pass"

        self.o = Mock()
        self.o.device_id = "test_id"
        self.o.pon_port.olt_device.volt_service = volt_service

    def tearDown(self):
        self.o = None
        sys.path = self.sys_path_save

    @requests_mock.Mocker()
    def test_enable(self, m):
        m.post("http://voltha_url:1234/api/v1/devices/test_id/enable")

        self.o.admin_state = "ENABLED"
        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_disable(self, m):
        m.post("http://voltha_url:1234/api/v1/devices/test_id/disable")

        self.o.admin_state = "DISABLED"
        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_disable_fail(self, m):
        m.post("http://voltha_url:1234/api/v1/devices/test_id/disable", status_code=500, text="Mock Error")

        self.o.admin_state = "DISABLED"

        with self.assertRaises(Exception) as e:
            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
            self.assertTrue(m.called)
            self.assertEqual(e.exception.message, "Failed to disable ONU device: Mock Error")

if __name__ == "__main__":
    unittest.main()
