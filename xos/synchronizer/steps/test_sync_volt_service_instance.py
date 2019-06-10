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
import functools
from mock import patch, call, Mock, PropertyMock
import requests_mock

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

class TestSyncVOLTServiceInstance(unittest.TestCase):
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
        mock_modelaccessor_config(test_path, [("olt-service", "volt.xproto"),
                                              ("rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        reload(xossynchronizer.modelaccessor)  # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from xossynchronizer.steps.syncstep import DeferredException
        from sync_volt_service_instance import SyncVOLTServiceInstance, model_accessor

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = SyncVOLTServiceInstance

        # create a mock ONOS Service
        onos = Mock()
        onos.name = "ONOS"
        onos.leaf_model.rest_hostname = "onos_voltha_url"
        onos.leaf_model.rest_port = 4321
        onos.leaf_model.rest_username = "onos_voltha_user"
        onos.leaf_model.rest_password = "onos_voltha_pass"

        volt_service = Mock()
        volt_service.provider_services = [onos]

        uni_port = Mock()
        uni_port.port_no = "uni_port_id"

        onu_device = Mock()
        onu_device.name = "BRCM1234"
        onu_device.pon_port.olt_device.dp_id = None
        onu_device.pon_port.olt_device.name = "Test OLT Device"
        onu_device.uni_ports.first.return_value = uni_port

        # create a mock service instance
        o = Mock()
        o.policy_code = 1
        o.id = 1
        o.owner_id = "volt_service"
        o.onu_device = onu_device
        o.tologdict.return_value = {}

        self.o = o
        self.onu_device = onu_device
        self.volt_service = volt_service

    def tearDown(self):
        self.o = None
        sys.path = self.sys_path_save

    @requests_mock.Mocker()
    def test_do_not_sync(self, m):
        self.onu_device.pon_port.olt_device.dp_id = None

        with patch.object(VOLTService.objects, "get") as olt_service_mock:
            olt_service_mock.return_value = self.volt_service

            with self.assertRaises(DeferredException) as e:
                self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

            self.assertFalse(m.called)
            self.assertEqual(e.exception.message, "Waiting for OLTDevice Test OLT Device to be synchronized")

    @requests_mock.Mocker()
    def test_do_sync(self, m):

        self.onu_device.pon_port.olt_device.dp_id = "of:dp_id"

        m.post("http://onos_voltha_url:4321/onos/olt/oltapp/of:dp_id/uni_port_id", status_code=200, json={})

        with patch.object(VOLTService.objects, "get") as olt_service_mock:
            olt_service_mock.return_value = self.volt_service

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
            self.assertTrue(m.called)
            self.assertEqual(self.o.backend_handle, "of:dp_id/uni_port_id")

    @requests_mock.Mocker()
    def test_do_sync_fail(self, m):

        m.post("http://onos_voltha_url:4321/onos/olt/oltapp/of:dp_id/uni_port_id", status_code=500, text="Mock Error")

        self.onu_device.pon_port.olt_device.dp_id = "of:dp_id"

        with patch.object(VOLTService.objects, "get") as olt_service_mock:
            olt_service_mock.return_value = self.volt_service

            with self.assertRaises(Exception) as e:
                self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
                self.assertTrue(m.called)
                self.assertEqual(e.exception.message, "Failed to add subscriber in onos voltha: Mock Error")

    @requests_mock.Mocker()
    def test_delete(self, m):
        m.delete("http://onos_voltha_url:4321/onos/olt/oltapp/of:dp_id/uni_port_id", status_code=204)

        self.onu_device.pon_port.olt_device.dp_id = "of:dp_id"
        self.o.backend_handle = "of:dp_id/uni_port_id"

        with patch.object(VOLTService.objects, "get") as olt_service_mock:
            olt_service_mock.return_value = self.volt_service

            self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)
            self.assertTrue(m.called)
            self.assertEqual(m.call_count, 1)

if __name__ == "__main__":
    unittest.main()
