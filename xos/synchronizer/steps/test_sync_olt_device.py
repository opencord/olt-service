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
# END of hack to load synchronizer framework

# Generate model from xproto
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

def match_onos_req(req):
    request = req.json()['devices']
    if not request['of:0000000ce2314000']:
        return False
    else:
        if not request['of:0000000ce2314000']['basic']['driver'] == 'pmc-olt':
            return False
        if not request['of:0000000ce2314000']['accessDevice']['vlan'] == "s_tag" or not request['of:0000000ce2314000']['accessDevice']['uplink'] == "129":
            return False
    return True

class TestSyncOLTDevice(unittest.TestCase):
    def setUp(self):
        self.sys_path_save = sys.path
        sys.path.append(xos_dir)
        sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../model_policies/test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END setting up the config module

        from synchronizers.new_base.mock_modelaccessor_build import build_mock_modelaccessor
        build_mock_modelaccessor(xos_dir, services_dir, [get_models_fn("olt-service", "volt.xproto")])
        import synchronizers.new_base.modelaccessor
        from sync_olt_device import SyncOLTDevice
        self.sync_step = SyncOLTDevice

        pon_port = Mock()
        pon_port.port_id = "00ff00"
        pon_port.s_tag = "s_tag"

        # Create a mock service instance
        o = Mock()
        o.volt_service.voltha_url = "voltha_url"
        o.volt_service.voltha_port = 1234
        o.volt_service.voltha_user = "voltha_user"
        o.volt_service.voltha_pass = "voltha_pass"
        o.volt_service.onos_voltha_url = "onos_voltha_url"
        o.volt_service.onos_voltha_port = 4321
        o.volt_service.onos_voltha_user = "onos_voltha_user"
        o.volt_service.onos_voltha_pass = "onos_voltha_pass"

        o.device_type = "ponsim_olt"
        o.host = "172.17.0.1"
        o.port = "50060"
        o.uplink = "129"
        o.driver = "pmc-olt"

        # feedback state
        o.device_id = None
        o.admin_state = None
        o.oper_status = None
        o.of_id = None

        o.tologdict.return_value = {'name': "Mock VOLTServiceInstance"}

        o.save.return_value = "Saved"

        o.ports.all.return_value = [pon_port]

        self.o = o

    def tearDown(self):
        self.o = None
        sys.path = self.sys_path_save

    @requests_mock.Mocker()
    def test_get_of_id_from_device(self, m):
        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
                {"root_device_id": "0001cc4974a62b87", "id": "0001000000000001"}
            ]
        }
        m.get("http://voltha_url:1234/api/v1/logical_devices", status_code=200, json=logical_devices)
        self.o.device_id = "123"
        self.o = self.sync_step.get_ids_from_logical_device(self.o)
        self.assertEqual(self.o.of_id, "0001000ce2314000")
        self.assertEqual(self.o.dp_id, "of:0000000ce2314000")

        with self.assertRaises(Exception) as e:
            self.o.device_id = "idonotexist"
            self.sync_step.get_ids_from_logical_device(self.o)
        self.assertEqual(e.exception.message, "Can't find a logical_device for OLT device id: idonotexist")

    @requests_mock.Mocker()
    def test_sync_record_fail_add(self, m):
        """
        Should print an error if we can't add the device in VOLTHA
        """
        m.post("http://voltha_url:1234/api/v1/devices", status_code=500, text="MockError")

        with self.assertRaises(Exception) as e:
            self.sync_step().sync_record(self.o)
        self.assertEqual(e.exception.message, "Failed to add OLT device: MockError")

    @requests_mock.Mocker()
    def test_sync_record_fail_no_id(self, m):
        """
        Should print an error if VOLTHA does not return the device id
        """
        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json={"id": ""})

        with self.assertRaises(Exception) as e:
            self.sync_step().sync_record(self.o)
        self.assertEqual(e.exception.message, "VOLTHA Device Id is empty. This probably means that the OLT device is already provisioned in VOLTHA")

    @requests_mock.Mocker()
    def test_sync_record_fail_enable(self, m):
        """
        Should print an error if device.enable fails
        """
        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json={"id": "123"})
        m.post("http://voltha_url:1234/api/v1/devices/123/enable", status_code=500, text="EnableError")

        with self.assertRaises(Exception) as e:
            self.sync_step().sync_record(self.o)

        self.assertEqual(e.exception.message, "Failed to enable OLT device: EnableError")

    @requests_mock.Mocker()
    def test_sync_record_success(self, m):
        """
        If device.enable succed should fetch the state, retrieve the of_id and push it to ONOS
        """
        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json={"id": "123"})
        m.post("http://voltha_url:1234/api/v1/devices/123/enable", status_code=200)
        m.get("http://voltha_url:1234/api/v1/devices/123", json={"oper_status": "ENABLED", "admin_state": "ACTIVE"})
        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
                {"root_device_id": "0001cc4974a62b87", "id": "0001000000000001"}
            ]
        }
        m.get("http://voltha_url:1234/api/v1/logical_devices", status_code=200, json=logical_devices)

        m.post("http://onos_voltha_url:4321/onos/v1/network/configuration/", status_code = 200, additional_matcher=match_onos_req, json={})

        # FIXME this is part of the block in the syncstep
        m.delete("http://onos_voltha_url:4321/onos/v1/network/configuration/devices/0001000ce2314000", status_code=200)

        self.sync_step().sync_record(self.o)
        self.assertEqual(self.o.admin_state, "ACTIVE")
        self.assertEqual(self.o.oper_status, "ENABLED")
        self.assertEqual(self.o.of_id, "0001000ce2314000")
        self.o.save.assert_called_once()

    @requests_mock.Mocker()
    def test_sync_record_already_existing_in_voltha(self, m):
        # mock device feedback state
        self.o.device_id = "123"
        self.o.admin_state = "ACTIVE"
        self.o.oper_status = "ENABLED"
        self.o.dp_id = "of:0000000ce2314000"
        self.o.of_id = "0001000ce2314000"

        m.post("http://onos_voltha_url:4321/onos/v1/network/configuration/", status_code = 200, additional_matcher=match_onos_req, json={})

        # FIXME this is part of the block in the syncstep
        m.delete("http://onos_voltha_url:4321/onos/v1/network/configuration/devices/0001000ce2314000", status_code=200)

        self.sync_step().sync_record(self.o)
        self.o.save.assert_not_called()

    @requests_mock.Mocker()
    def test_delete_record(self, m):
        self.o.of_id = "0001000ce2314000"
        self.o.device_id = "123"

        m.delete("http://onos_voltha_url:4321/onos/v1/network/configuration/devices/0001000ce2314000", status_code=200)
        m.post("http://voltha_url:1234/api/v1/devices/123/disable", status_code=200)
        m.delete("http://voltha_url:1234/api/v1/devices/123/delete", status_code=200)

        self.sync_step().delete_record(self.o)

        # We don't need to assert here if there are no exceptions happening

if __name__ == "__main__":
    unittest.main()
