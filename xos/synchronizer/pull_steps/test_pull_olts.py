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
import grpc
import os
import sys

from concurrent.futures import ThreadPoolExecutor
from mock import patch, call, Mock, PropertyMock

test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mock_voltha_server import VolthaServerMock, MOCK_VOLTHA_SERVER_ADDRESS, MOCK_VOLTHA_SERVER_PORT
from voltha_client import clear_voltha_client_cache


class TestSyncOLTDevice(unittest.TestCase):

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

        from pull_olts import OLTDevicePullStep

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = OLTDevicePullStep

        # mock volt service
        self.volt_service = Mock()
        self.volt_service.id = "volt_service_id"
        self.volt_service.voltha_url = MOCK_VOLTHA_SERVER_ADDRESS
        self.volt_service.voltha_port = MOCK_VOLTHA_SERVER_PORT

        # Mock gRPC server for simulated OLTs
        clear_voltha_client_cache()
        self.server = grpc.server(ThreadPoolExecutor(max_workers=5))
        self.voltha_mock, _, _, = VolthaServerMock.start_voltha_server(self.server)

        # VOLTHA server responses
        self.devices = {
            "items": [
                {
                    "id": "test_id",
                    "type": "simulated_olt",
                    "host_and_port": "172.17.0.1:50060",
                    "admin_state": "ENABLED",
                    "oper_status": "ACTIVE",
                    "serial_number": "serial_number",
                }
            ]
        }

        self.logical_devices = {
            "items": [
                {
                    "root_device_id": "test_id",
                    "id": "of_id",
                    "datapath_id": "55334486016"
                }
            ]
        }

        self.ports_dict = {
            "test_id": {
                "items": [
                    {
                        "label": "PON port",
                        "port_no": 1,
                        "type": "PON_OLT",
                        "admin_state": "ENABLED",
                        "oper_status": "ACTIVE"
                    },
                    {
                        "label": "NNI facing Ethernet port",
                        "port_no": 2,
                        "type": "ETHERNET_NNI",
                        "admin_state": "ENABLED",
                        "oper_status": "ACTIVE"
                    }
                ]
            }
        }

    def tearDown(self):
        self.server.stop(None)
        sys.path = self.sys_path_save

    def test_pull_host_and_port(self):
        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice, "save", autospec=True) as mock_olt_save, \
                patch.object(PONPort, "save") as mock_pon_save, \
                patch.object(NNIPort, "save") as mock_nni_save:
            olt_service_mock.return_value = [self.volt_service]
            self.voltha_mock.set_logical_devices(self.logical_devices)
            self.voltha_mock.set_devices(self.devices)
            self.voltha_mock.set_ports(self.ports_dict)

            self.sync_step(model_accessor=self.model_accessor).pull_records()

            saved_olts = mock_olt_save.call_args_list
            print(saved_olts)
            simulated_olt = saved_olts[0][0][0]
            self.assertEqual(len(saved_olts), 1)

            self.assertEqual(simulated_olt.admin_state, "ENABLED")
            self.assertEqual(simulated_olt.oper_status, "ACTIVE")
            self.assertEqual(simulated_olt.volt_service_id, "volt_service_id")
            self.assertEqual(simulated_olt.device_id, "test_id")
            self.assertEqual(simulated_olt.of_id, "of_id")
            self.assertEqual(simulated_olt.dp_id, "of:0000000ce2314000")

            mock_pon_save.assert_called()
            mock_nni_save.assert_called()

    def test_pull_mac_address(self):
        devices = {
            "items": [
                {
                    'id': 'tibit_id',
                    'type': 'tibit_olt',
                    'mac_address': '70:b3:d5:52:30:6f',
                    'admin_state': 'ENABLED',
                    'oper_status': 'ACTIVE',
                    'serial_number': 'OLT-70b3d552306f',
                }
            ]
        }

        logical_devices = {
            "items": [
                {
                    "root_device_id": "tibit_id",
                    "id": "of_id",
                    "datapath_id": "55334486017"
                }
            ]
        }
        self.ports_dict["tibit_id"] = self.ports_dict["test_id"]

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice, "save", autospec=True) as mock_olt_save, \
                patch.object(PONPort, "save") as mock_pon_save, \
                patch.object(NNIPort, "save") as mock_nni_save:
            olt_service_mock.return_value = [self.volt_service]

            self.voltha_mock.set_logical_devices(logical_devices)
            self.voltha_mock.set_devices(devices)
            self.voltha_mock.set_ports(self.ports_dict)

            self.sync_step(model_accessor=self.model_accessor).pull_records()

            saved_olts = mock_olt_save.call_args_list
            tibit_olt = saved_olts[0][0][0]
            self.assertEqual(len(saved_olts), 1)

            self.assertEqual(tibit_olt.admin_state, "ENABLED")
            self.assertEqual(tibit_olt.oper_status, "ACTIVE")
            self.assertEqual(tibit_olt.volt_service_id, "volt_service_id")
            self.assertEqual(tibit_olt.device_id, "tibit_id")
            self.assertEqual(tibit_olt.of_id, "of_id")
            self.assertEqual(tibit_olt.dp_id, "of:0000000ce2314001")

            mock_pon_save.assert_called()
            mock_nni_save.assert_called()

    def test_pull_existing(self):
        existing_olt = Mock()
        existing_olt.admin_state = "ENABLED"
        existing_olt.enacted = 2
        existing_olt.updated = 1
        existing_olt.serial_number = ""

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "filter") as mock_get, \
                patch.object(PONPort, "save") as mock_pon_save, \
                patch.object(NNIPort, "save") as mock_nni_save, \
                patch.object(existing_olt, "save") as  mock_olt_save:
            olt_service_mock.return_value = [self.volt_service]
            mock_get.return_value = [existing_olt]

            self.voltha_mock.set_logical_devices(self.logical_devices)
            self.voltha_mock.set_devices(self.devices)
            self.voltha_mock.set_ports(self.ports_dict)

            self.sync_step(model_accessor=self.model_accessor).pull_records()

            self.assertEqual(existing_olt.admin_state, "ENABLED")
            self.assertEqual(existing_olt.oper_status, "ACTIVE")
            self.assertEqual(existing_olt.volt_service_id, "volt_service_id")
            self.assertEqual(existing_olt.device_id, "test_id")
            self.assertEqual(existing_olt.of_id, "of_id")
            self.assertEqual(existing_olt.dp_id, "of:0000000ce2314000")
            self.assertEqual(existing_olt.serial_number, "serial_number")

            # mock_olt_save.assert_called()
            mock_pon_save.assert_called()
            mock_nni_save.assert_called()

    def test_pull_existing_empty_voltha_serial(self):
        existing_olt = Mock()
        existing_olt.admin_state = "ENABLED"
        existing_olt.enacted = 2
        existing_olt.updated = 1
        existing_olt.serial_number = "orig_serial"

        self.devices["items"][0]["serial_number"] = ""

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "filter") as mock_get, \
                patch.object(PONPort, "save") as mock_pon_save, \
                patch.object(NNIPort, "save") as mock_nni_save, \
                patch.object(existing_olt, "save") as  mock_olt_save:
            olt_service_mock.return_value = [self.volt_service]
            mock_get.return_value = [existing_olt]

            self.voltha_mock.set_logical_devices(self.logical_devices)
            self.voltha_mock.set_devices(self.devices)
            self.voltha_mock.set_ports(self.ports_dict)

            self.sync_step(model_accessor=self.model_accessor).pull_records()

            self.assertEqual(existing_olt.admin_state, "ENABLED")
            self.assertEqual(existing_olt.oper_status, "ACTIVE")
            self.assertEqual(existing_olt.volt_service_id, "volt_service_id")
            self.assertEqual(existing_olt.device_id, "test_id")
            self.assertEqual(existing_olt.of_id, "of_id")
            self.assertEqual(existing_olt.dp_id, "of:0000000ce2314000")
            self.assertEqual(existing_olt.serial_number, "orig_serial")

            # mock_olt_save.assert_called()
            mock_pon_save.assert_called()
            mock_nni_save.assert_called()

    def test_pull_existing_incorrect_voltha_serial(self):
        existing_olt = Mock()
        existing_olt.admin_state = "ENABLED"
        existing_olt.enacted = 2
        existing_olt.updated = 1
        existing_olt.serial_number = "orig_serial"

        self.devices["items"][0]["serial_number"] = "wrong_serial"

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "filter") as mock_get, \
                patch.object(PONPort, "save") as mock_pon_save, \
                patch.object(NNIPort, "save") as mock_nni_save, \
                patch.object(existing_olt, "save") as  mock_olt_save:
            olt_service_mock.return_value = [self.volt_service]
            mock_get.return_value = [existing_olt]

            self.voltha_mock.set_logical_devices(self.logical_devices)
            self.voltha_mock.set_devices(self.devices)
            self.voltha_mock.set_ports(self.ports_dict)

            self.sync_step(model_accessor=self.model_accessor).pull_records()

            self.assertEqual(existing_olt.backend_code, 2)
            self.assertEqual(existing_olt.backend_status, "Incorrect serial number")
            self.assertEqual(existing_olt.serial_number, "orig_serial")

    def test_pull_existing_do_not_sync(self):
        existing_olt = Mock()
        existing_olt.enacted = 1
        existing_olt.updated = 2
        existing_olt.device_id = "test_id"

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "filter") as mock_get, \
                patch.object(PONPort, "save") as mock_pon_save, \
                patch.object(NNIPort, "save") as mock_nni_save, \
                patch.object(existing_olt, "save") as mock_olt_save:
            olt_service_mock.return_value = [self.volt_service]
            mock_get.return_value = [existing_olt]
            self.voltha_mock.set_logical_devices(self.logical_devices)
            self.voltha_mock.set_devices(self.devices)
            self.voltha_mock.set_ports(self.ports_dict)

            self.sync_step(model_accessor=self.model_accessor).pull_records()

            mock_olt_save.assert_not_called()
            mock_pon_save.assert_called()
            mock_nni_save.assert_called()

    def test_pull_deleted_object(self):
        existing_olt = Mock()
        existing_olt.enacted = 2
        existing_olt.updated = 1
        existing_olt.device_id = "test_id"

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "get_items") as mock_get, \
                patch.object(existing_olt, "delete") as mock_olt_delete:
            olt_service_mock.return_value = [self.volt_service]
            mock_get.return_value = [existing_olt]

            self.sync_step(model_accessor=self.model_accessor).pull_records()

            mock_olt_delete.assert_called()


if __name__ == "__main__":
    unittest.main()
