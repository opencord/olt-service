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

import functools
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

class TestPullONUDevice(unittest.TestCase):

    def setUp(self):
        global DeferredException

        self.sys_path_save = sys.path
        sys.path.append(xos_dir)
        sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
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
        from pull_onus import ONUDevicePullStep, model_accessor

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = ONUDevicePullStep

        # mock volt service
        self.volt_service = Mock()
        self.volt_service.id = "volt_service_id"
        self.volt_service.voltha_url = "voltha_url"
        self.volt_service.voltha_user = "voltha_user"
        self.volt_service.voltha_pass = "voltha_pass"
        self.volt_service.voltha_port = 1234

        # mock OLTDevice
        self.olt = Mock()
        self.olt.id = 1

        # second mock OLTDevice
        self.olt2 = Mock()
        self.olt2.id = 2

        # mock pon port
        self.pon_port = Mock()
        self.pon_port.id = 1

        # mock pon port
        self.pon_port2 = Mock()
        self.pon_port2.id = 2

        # mock voltha responses
        self.devices = {
            "items": [
                {
                    "id": "0001130158f01b2d",
                    "type": "broadcom_onu",
                    "vendor": "Broadcom",
                    "serial_number": "BRCM22222222",
                    "vendor_id": "BRCM",
                    "adapter": "broadcom_onu",
                    "vlan": 0,
                    "admin_state": "ENABLED",
                    "oper_status": "ACTIVE",
                    "connect_status": "REACHABLE",
                    "reason": "starting-omci",
                    "parent_id": "00010fc93996afea",
                    "parent_port_no": 1
                }
            ]
        }

        self.two_devices = {
            "items": [
                {
                    "id": "0001130158f01b2d",
                    "type": "broadcom_onu",
                    "vendor": "Broadcom",
                    "serial_number": "BRCM22222222",
                    "vendor_id": "BRCM",
                    "adapter": "broadcom_onu",
                    "vlan": 0,
                    "admin_state": "ENABLED",
                    "oper_status": "ACTIVE",
                    "connect_status": "REACHABLE",
                    "reason": "starting-omci",
                    "parent_id": "00010fc93996afea",
                    "parent_port_no": 1
                },
                {
                    "id": "0001130158f01b2e",
                    "type": "broadcom_onu",
                    "vendor": "Broadcom",
                    "serial_number": "BRCM22222223",
                    "vendor_id": "BRCM",
                    "adapter": "broadcom_onu",
                    "vlan": 0,
                    "admin_state": "ENABLED",
                    "oper_status": "ACTIVE",
                    "connect_status": "REACHABLE",
                    "reason": "omci-admin-lock",
                    "parent_id": "00010fc93996afeb",
                    "parent_port_no": 1
                }
            ],
        }

        # TODO add ports
        self.ports = {
            "items": []
        }

    def tearDown(self):
        sys.path = self.sys_path_save

    @requests_mock.Mocker()
    def test_missing_volt_service(self, m):
            self.assertFalse(m.called)

    @requests_mock.Mocker()
    def test_pull(self, m):

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "get") as mock_olt_device, \
                patch.object(PONPort.objects, "get") as mock_pon_port, \
                patch.object(ONUDevice, "save", autospec=True) as mock_save:
            olt_service_mock.return_value = [self.volt_service]
            mock_pon_port.return_value = self.pon_port
            mock_olt_device.return_value = self.olt

            m.get("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.devices)
            m.get("http://voltha_url:1234/api/v1/devices/0001130158f01b2d/ports", status_code=200, json=self.ports)

            self.sync_step().pull_records()

            saved_onu = mock_save.call_args[0][0]

            self.assertEqual(saved_onu.admin_state, "ENABLED")
            self.assertEqual(saved_onu.oper_status, "ACTIVE")
            self.assertEqual(saved_onu.connect_status, "REACHABLE")
            self.assertEqual(saved_onu.reason, "starting-omci")
            self.assertEqual(saved_onu.device_type, "broadcom_onu")
            self.assertEqual(saved_onu.vendor, "Broadcom")
            self.assertEqual(saved_onu.device_id, "0001130158f01b2d")

            self.assertEqual(mock_save.call_count, 1)

    @requests_mock.Mocker()
    def test_pull_bad_pon(self, m):

        def olt_side_effect(device_id):
            # fail the first onu device
            if device_id=="00010fc93996afea":
                return self.olt
            else:
                return self.olt2

        def pon_port_side_effect(mock_pon_port, port_no, olt_device_id):
            # fail the first onu device
            if olt_device_id==1:
                raise IndexError()
            return self.pon_port2

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "get") as mock_olt_device, \
                patch.object(PONPort.objects, "get") as mock_pon_port, \
                patch.object(ONUDevice, "save", autospec=True) as mock_save:
            olt_service_mock.return_value = [self.volt_service]
            mock_pon_port.side_effect = functools.partial(pon_port_side_effect, self.pon_port)
            mock_olt_device.side_effect = olt_side_effect

            m.get("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.two_devices)
            m.get("http://voltha_url:1234/api/v1/devices/0001130158f01b2d/ports", status_code=200, json=self.ports)
            m.get("http://voltha_url:1234/api/v1/devices/0001130158f01b2e/ports", status_code=200, json=self.ports)

            self.sync_step().pull_records()

            self.assertEqual(mock_save.call_count, 1)
            saved_onu = mock_save.call_args[0][0]

            # we should get the second onu in self.two_onus

            self.assertEqual(saved_onu.admin_state, "ENABLED")
            self.assertEqual(saved_onu.oper_status, "ACTIVE")
            self.assertEqual(saved_onu.connect_status, "REACHABLE")
            self.assertEqual(saved_onu.reason, "omci-admin-lock")
            self.assertEqual(saved_onu.device_type, "broadcom_onu")
            self.assertEqual(saved_onu.vendor, "Broadcom")
            self.assertEqual(saved_onu.device_id, "0001130158f01b2e")

            self.assertEqual(mock_save.call_count, 1)

    @requests_mock.Mocker()
    def test_pull_bad_olt(self, m):

        def olt_side_effect(device_id):
            # fail the first onu device
            if device_id=="00010fc93996afea":
                raise IndexError()
            else:
                return self.olt2

        with patch.object(VOLTService.objects, "all") as olt_service_mock, \
                patch.object(OLTDevice.objects, "get") as mock_olt_device, \
                patch.object(PONPort.objects, "get") as mock_pon_port, \
                patch.object(ONUDevice, "save", autospec=True) as mock_save:
            olt_service_mock.return_value = [self.volt_service]
            mock_pon_port.return_value = self.pon_port2
            mock_olt_device.side_effect = olt_side_effect

            m.get("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.two_devices)
            m.get("http://voltha_url:1234/api/v1/devices/0001130158f01b2d/ports", status_code=200, json=self.ports)
            m.get("http://voltha_url:1234/api/v1/devices/0001130158f01b2e/ports", status_code=200, json=self.ports)

            self.sync_step().pull_records()

            self.assertEqual(mock_save.call_count, 1)
            saved_onu = mock_save.call_args[0][0]

            # we should get the second onu in self.two_onus

            self.assertEqual(saved_onu.admin_state, "ENABLED")
            self.assertEqual(saved_onu.oper_status, "ACTIVE")
            self.assertEqual(saved_onu.connect_status, "REACHABLE")
            self.assertEqual(saved_onu.reason, "omci-admin-lock")
            self.assertEqual(saved_onu.device_type, "broadcom_onu")
            self.assertEqual(saved_onu.vendor, "Broadcom")
            self.assertEqual(saved_onu.device_id, "0001130158f01b2e")

            self.assertEqual(mock_save.call_count, 1)


if __name__ == "__main__":
    unittest.main()