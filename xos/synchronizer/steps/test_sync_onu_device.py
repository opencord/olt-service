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
import os
import sys
import grpc

from concurrent.futures import ThreadPoolExecutor
from mock import patch, call, Mock, PropertyMock

test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mock_voltha_server import VolthaServerMock, MOCK_VOLTHA_SERVER_ADDRESS, MOCK_VOLTHA_SERVER_PORT
from voltha_client import clear_voltha_client_cache


class TestSyncONUDevice(unittest.TestCase):
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
                                              ("rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        reload(xossynchronizer.modelaccessor)  # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from xossynchronizer.modelaccessor import model_accessor
        from sync_onu_device import SyncONUDevice

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = SyncONUDevice

        volt_service = Mock()
        volt_service.voltha_url = MOCK_VOLTHA_SERVER_ADDRESS
        volt_service.voltha_port = MOCK_VOLTHA_SERVER_PORT

        self.o = Mock()
        self.o.device_id = "test_id"
        self.o.pon_port.olt_device.volt_service = volt_service

        clear_voltha_client_cache()
        self.server = grpc.server(ThreadPoolExecutor(max_workers=5))
        self.voltha_mock, _, _ = VolthaServerMock.start_voltha_server(self.server)

    def tearDown(self):
        self.server.stop(None)
        self.o = None
        sys.path = self.sys_path_save

    def test_enable(self):
        self.o.admin_state = "ENABLED"
        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertEqual(self.voltha_mock.enable_called, 1)

    def test_disable(self):
        self.o.admin_state = "DISABLED"
        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertEqual(self.voltha_mock.disable_called, 1)

    def test_admin_disabled(self):
        self.o.admin_state = "ADMIN_DISABLED"
        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertEqual(self.voltha_mock.disable_called, 1)

    def test_disable_fail(self):
        self.o.admin_state = "DISABLED"

        with self.assertRaises(Exception) as e:
            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
            self.assertTrue(self.voltha_mock.disable_called)
            self.assertEqual(e.exception.message, "Failed to disable ONU device: Mock Error")


if __name__ == "__main__":
    unittest.main()
