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

# Hack to load synchronizer framework
test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
xos_dir=os.path.join(test_path, "../../..")
if not os.path.exists(os.path.join(test_path, "new_base")):
    xos_dir=os.path.join(test_path, "../../../../../../orchestration/xos/xos")
    services_dir = os.path.join(xos_dir, "../../xos_services")
sys.path.append(xos_dir)
sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))
# END Hack to load synchronizer framework

# generate model from xproto
def get_models_fn(service_name, xproto_name):
    name = os.path.join(service_name, "xos", xproto_name)
    if os.path.exists(os.path.join(services_dir, name)):
        return name
    else:
        name = os.path.join(service_name, "xos", "synchronizer", "models", xproto_name)
        if os.path.exists(os.path.join(services_dir, name)):
            return name
    raise Exception("Unable to find service=%s xproto=%s" % (service_name, xproto_name))
# END generate model from xproto

class TestSyncOLTDevice(unittest.TestCase):

    def setUp(self):
        global DeferredException

        self.sys_path_save = sys.path
        sys.path.append(xos_dir)
        sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../model_policies/test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from synchronizers.new_base.mock_modelaccessor_build import build_mock_modelaccessor
        # build_mock_modelaccessor(xos_dir, services_dir, [get_models_fn("olt-service", "volt.xproto")])

        # FIXME this is to get jenkins to pass the tests, somehow it is running tests in a different order
        # and apparently it is not overriding the generated model accessor
        build_mock_modelaccessor(xos_dir, services_dir, [get_models_fn("olt-service", "volt.xproto"),
                                                         get_models_fn("vsg", "vsg.xproto"),
                                                         get_models_fn("../profiles/rcord", "rcord.xproto")])
        import synchronizers.new_base.modelaccessor
        from pull_olts import OLTDevicePullStep, model_accessor

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = OLTDevicePullStep

        # mock volt service
        self.volt_service = Mock()
        self.volt_service.id = "volt_service_id"
        self.volt_service.voltha_url = "voltha_url"
        self.volt_service.voltha_user = "voltha_user"
        self.volt_service.voltha_pass = "voltha_pass"
        self.volt_service.voltha_port = 1234

        # mock voltha responses
        self.devices = {
            "items": [
                {
                    "id": "test_id",
                    "type": "simulated_olt",
                    "host_and_port": "172.17.0.1:50060",
                    "admin_state": "ENABLED",
                    "oper_status": "ACTIVE"
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

        self.ports = {
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

    def tearDown(self):
        sys.path = self.sys_path_save

    @requests_mock.Mocker()
    def test_missing_volt_service(self, m):
            self.assertFalse(m.called)

    @requests_mock.Mocker()
    def test_pull(self, m):

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice, "save") as mock_olt_save, \
                patch.object(PONPort, "save") as mock_pon_save, \
                patch.object(NNIPort, "save") as mock_nni_save:
            olt_service_mock.return_value = [self.volt_service]

            m.get("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.devices)
            m.get("http://voltha_url:1234/api/v1/devices/test_id/ports", status_code=200, json=self.ports)
            m.get("http://voltha_url:1234/api/v1/logical_devices", status_code=200, json=self.logical_devices)

            self.sync_step().pull_records()

            # TODO how to asster this?
            # self.assertEqual(existing_olt.admin_state, "ENABLED")
            # self.assertEqual(existing_olt.oper_status, "ACTIVE")
            # self.assertEqual(existing_olt.volt_service_id, "volt_service_id")
            # self.assertEqual(existing_olt.device_id, "test_id")
            # self.assertEqual(existing_olt.of_id, "of_id")
            # self.assertEqual(existing_olt.dp_id, "of:0000000ce2314000")

            mock_olt_save.assert_called()
            mock_pon_save.assert_called()
            mock_nni_save.assert_called()

    @requests_mock.Mocker()
    def test_pull_existing(self, m):

        existing_olt = Mock()
        existing_olt.enacted = 2
        existing_olt.updated = 1

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "filter") as mock_get, \
                patch.object(PONPort, "save") as mock_pon_save, \
                patch.object(NNIPort, "save") as mock_nni_save, \
                patch.object(existing_olt, "save") as  mock_olt_save:
            olt_service_mock.return_value = [self.volt_service]
            mock_get.return_value = [existing_olt]

            m.get("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.devices)
            m.get("http://voltha_url:1234/api/v1/devices/test_id/ports", status_code=200, json=self.ports)
            m.get("http://voltha_url:1234/api/v1/logical_devices", status_code=200, json=self.logical_devices)

            self.sync_step().pull_records()

            self.assertEqual(existing_olt.admin_state, "ENABLED")
            self.assertEqual(existing_olt.oper_status, "ACTIVE")
            self.assertEqual(existing_olt.volt_service_id, "volt_service_id")
            self.assertEqual(existing_olt.device_id, "test_id")
            self.assertEqual(existing_olt.of_id, "of_id")
            self.assertEqual(existing_olt.dp_id, "of:0000000ce2314000")

            mock_olt_save.assert_called()
            mock_pon_save.assert_called()
            mock_nni_save.assert_called()

    @requests_mock.Mocker()
    def test_pull_existing_do_not_sync(self, m):
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

            m.get("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.devices)
            m.get("http://voltha_url:1234/api/v1/devices/test_id/ports", status_code=200, json=self.ports)
            m.get("http://voltha_url:1234/api/v1/logical_devices", status_code=200, json=self.logical_devices)

            self.sync_step().pull_records()

            mock_olt_save.assert_not_called()
            mock_pon_save.assert_called()
            mock_nni_save.assert_called()

if __name__ == "__main__":
    unittest.main()