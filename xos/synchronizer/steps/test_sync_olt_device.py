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

from requests import ConnectionError
import unittest
import functools
from mock import patch, call, Mock, PropertyMock
import requests_mock

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

def match_json(desired, req):
    if desired!=req.json():
        raise Exception("Got request %s, but body is not matching" % req.url)
        return False
    return True

class TestSyncOLTDevice(unittest.TestCase):
    def setUp(self):
        global DeferredException
        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END setting up the config module

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("olt-service", "volt.xproto"),
                                                ("rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from sync_olt_device import SyncOLTDevice, DeferredException
        self.sync_step = SyncOLTDevice

        pon_port = Mock()
        pon_port.port_id = "00ff00"

        # Create a mock OLTDevice
        o = Mock()
        o.volt_service.voltha_url = "voltha_url"
        o.volt_service.voltha_port = 1234
        o.volt_service.voltha_user = "voltha_user"
        o.volt_service.voltha_pass = "voltha_pass"

        o.volt_service.onos_voltha_port = 4321
        o.volt_service.onos_voltha_url = "onos"
        o.volt_service.onos_voltha_user = "karaf"
        o.volt_service.onos_voltha_pass = "karaf"

        o.device_type = "ponsim_olt"
        o.host = "172.17.0.1"
        o.port = "50060"
        o.uplink = "129"
        o.driver = "voltha"
        o.name = "Test Device"
        o.admin_state = "ENABLED"

        # feedback state
        o.device_id = None
        o.oper_status = None
        o.of_id = None
        o.id = 1

        o.tologdict.return_value = {'name': "Mock VOLTServiceInstance"}

        o.save_changed_fields.return_value = "Saved"

        o.pon_ports.all.return_value = [pon_port]

        self.o = o

        self.voltha_devices_response = {"id": "123", "serial_number": "foobar"}

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
            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertEqual(e.exception.message, "Failed to add OLT device: MockError")

    @requests_mock.Mocker()
    def test_sync_record_fail_no_id(self, m):
        """
        Should print an error if VOLTHA does not return the device id
        """
        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json={"id": ""})

        with self.assertRaises(Exception) as e:
            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertEqual(e.exception.message, "VOLTHA Device Id is empty. This probably means that the OLT device is already provisioned in VOLTHA")

    @requests_mock.Mocker()
    def test_sync_record_fail_enable(self, m):
        """
        Should print an error if device.enable fails
        """
        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.voltha_devices_response)
        m.post("http://voltha_url:1234/api/v1/devices/123/enable", status_code=500, text="EnableError")

        with self.assertRaises(Exception) as e:
            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        self.assertEqual(e.exception.message, "Failed to enable OLT device: EnableError")

    @requests_mock.Mocker()
    def test_sync_record_success(self, m):
        """
        If device.enable succed should fetch the state, retrieve the of_id and push it to ONOS
        """

        expected_conf = {
            "type": self.o.device_type,
            "host_and_port": "%s:%s" % (self.o.host, self.o.port)
        }

        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.voltha_devices_response, additional_matcher=functools.partial(match_json, expected_conf))
        m.post("http://voltha_url:1234/api/v1/devices/123/enable", status_code=200)
        m.get("http://voltha_url:1234/api/v1/devices/123", json={"oper_status": "ACTIVE", "admin_state": "ENABLED", "serial_number": "foobar"})
        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
                {"root_device_id": "0001cc4974a62b87", "id": "0001000000000001"}
            ]
        }
        m.get("http://voltha_url:1234/api/v1/logical_devices", status_code=200, json=logical_devices)

        onos_expected_conf = {
            "devices": {
                "of:0000000ce2314000": {
                    "basic": {
                        "name": self.o.name
                    }
                }
            }
        }
        m.post("http://onos:4321/onos/v1/network/configuration/", status_code=200, json=onos_expected_conf,
               additional_matcher=functools.partial(match_json, onos_expected_conf))

        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertEqual(self.o.admin_state, "ENABLED")
        self.assertEqual(self.o.oper_status, "ACTIVE")
        self.assertEqual(self.o.serial_number, "foobar")
        self.assertEqual(self.o.of_id, "0001000ce2314000")

        # One save during preprovision
        # One save during activation to set backend_status to "Waiting for device to activate"
        # One save after activation has succeeded
        self.assertEqual(self.o.save_changed_fields.call_count, 3)

    @requests_mock.Mocker()
    def test_sync_record_success_mac_address(self, m):
        """
        A device should be pre-provisioned via mac_address, the the process is the same
        """

        del self.o.host
        del self.o.port
        self.o.mac_address = "00:0c:e2:31:40:00"

        expected_conf = {
            "type": self.o.device_type,
            "mac_address": self.o.mac_address
        }

        onos_expected_conf = {
            "devices": {
                "of:0000000ce2314000": {
                    "basic": {
                        "name": self.o.name
                    }
                }
            }
        }
        m.post("http://onos:4321/onos/v1/network/configuration/", status_code=200, json=onos_expected_conf,
               additional_matcher=functools.partial(match_json, onos_expected_conf))

        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.voltha_devices_response,
               additional_matcher=functools.partial(match_json, expected_conf))
        m.post("http://voltha_url:1234/api/v1/devices/123/enable", status_code=200)
        m.get("http://voltha_url:1234/api/v1/devices/123", json={"oper_status": "ACTIVE", "admin_state": "ENABLED", "serial_number": "foobar"})
        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
                {"root_device_id": "0001cc4974a62b87", "id": "0001000000000001"}
            ]
        }
        m.get("http://voltha_url:1234/api/v1/logical_devices", status_code=200, json=logical_devices)

        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.assertEqual(self.o.admin_state, "ENABLED")
        self.assertEqual(self.o.oper_status, "ACTIVE")
        self.assertEqual(self.o.of_id, "0001000ce2314000")

        # One save during preprovision
        # One save during activation to set backend_status to "Waiting for device to activate"
        # One save after activation has succeeded
        self.assertEqual(self.o.save_changed_fields.call_count, 3)

    @requests_mock.Mocker()
    def test_sync_record_enable_timeout(self, m):
        """
        If device activation fails we need to tell the user.

        OLT will be preprovisioned.
        OLT will return "ERROR" for oper_status during activate and will eventually exceed retries.s
        """

        expected_conf = {
            "type": self.o.device_type,
            "host_and_port": "%s:%s" % (self.o.host, self.o.port)
        }

        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.voltha_devices_response,
               additional_matcher=functools.partial(match_json, expected_conf))
        m.post("http://voltha_url:1234/api/v1/devices/123/enable", status_code=200)
        m.get("http://voltha_url:1234/api/v1/devices/123", [
                  {"json": {"oper_status": "ACTIVATING", "admin_state": "ENABLED", "serial_number": "foobar"}, "status_code": 200},
                  {"json": {"oper_status": "ERROR", "admin_state": "ENABLED", "serial_number": "foobar"}, "status_code": 200}
              ])

        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
                {"root_device_id": "0001cc4974a62b87", "id": "0001000000000001"}
            ]
        }
        m.get("http://voltha_url:1234/api/v1/logical_devices", status_code=200, json=logical_devices)

        with self.assertRaises(Exception) as e:
            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        self.assertEqual(e.exception.message, "It was not possible to activate OLTDevice with id 1")
        self.assertEqual(self.o.oper_status, "ERROR")
        self.assertEqual(self.o.admin_state, "ENABLED")
        self.assertEqual(self.o.device_id, "123")
        self.assertEqual(self.o.serial_number, "foobar")

        # One save from preprovision to set device_id, serial_number
        # One save from activate to set backend_status to "Waiting for device to be activated"
        self.assertEqual(self.o.save_changed_fields.call_count, 2)

    @requests_mock.Mocker()
    def test_sync_record_already_existing_in_voltha(self, m):
        """
        If device.admin_state == "ENABLED" and oper_status == "ACTIVE", then the OLT should not be reactivated.
        """

        # mock device feedback state
        self.o.device_id = "123"
        self.o.admin_state = "ENABLED"
        self.o.oper_status = "ACTIVE"
        self.o.dp_id = "of:0000000ce2314000"
        self.o.of_id = "0001000ce2314000"

        expected_conf = {
            "devices": {
                self.o.dp_id: {
                    "basic": {
                        "name": self.o.name
                    }
                }
            }
        }
        m.post("http://onos:4321/onos/v1/network/configuration/", status_code=200, json=expected_conf,
               additional_matcher=functools.partial(match_json, expected_conf))

        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.o.save.assert_not_called()
        self.o.save_changed_fields.assert_not_called()


    @requests_mock.Mocker()
    def test_sync_record_deactivate(self, m):
        """
        If device.admin_state == "DISABLED" and oper_status == "ACTIVE", then OLT should be deactivated.
        """

        expected_conf = {
            "type": self.o.device_type,
            "host_and_port": "%s:%s" % (self.o.host, self.o.port)
        }

        # Make it look like we have an active OLT that we are deactivating.
        self.o.admin_state = "DISABLED"
        self.o.oper_status = "ACTIVE"
        self.o.serial_number = "foobar"
        self.o.device_id = "123"
        self.o.of_id = "0001000ce2314000"

        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.voltha_devices_response, additional_matcher=functools.partial(match_json, expected_conf))
        m.post("http://voltha_url:1234/api/v1/devices/123/disable", status_code=200)

        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        # No saves as state has not changed (will eventually be saved by synchronizer framework to update backend_status)
        self.assertEqual(self.o.save.call_count, 0)
        self.assertEqual(self.o.save_changed_fields.call_count, 0)


        # Make sure disable was called
        urls = [x.url for x in m.request_history]
        self.assertIn("http://voltha_url:1234/api/v1/devices/123/disable", urls)

    @requests_mock.Mocker()
    def test_sync_record_deactivate_already_inactive(self, m):
        """
        If device.admin_state == "DISABLED" and device.oper_status == "UNKNOWN", then the device is already deactivated
        and VOLTHA should not be called.
        """

        expected_conf = {
            "type": self.o.device_type,
            "host_and_port": "%s:%s" % (self.o.host, self.o.port)
        }

        # Make it look like we have an active OLT that we are deactivating.
        self.o.admin_state = "DISABLED"
        self.o.oper_status = "UNKNOWN"
        self.o.serial_number = "foobar"
        self.o.device_id = "123"
        self.o.of_id = "0001000ce2314000"

        m.post("http://voltha_url:1234/api/v1/devices", status_code=200, json=self.voltha_devices_response, additional_matcher=functools.partial(match_json, expected_conf))

        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        # No saves as state has not changed (will eventually be saved by synchronizer framework to update backend_status)
        self.assertEqual(self.o.save.call_count, 0)
        self.assertEqual(self.o.save_changed_fields.call_count, 0)

    @requests_mock.Mocker()
    def test_delete_record(self, m):
        self.o.of_id = "0001000ce2314000"
        self.o.device_id = "123"

        m.post("http://voltha_url:1234/api/v1/devices/123/disable", status_code=200)
        m.delete("http://voltha_url:1234/api/v1/devices/123/delete", status_code=200)

        self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)

        self.assertEqual(m.call_count, 2)

    @patch('requests.post')
    def test_delete_record_connectionerror(self, m):
        self.o.of_id = "0001000ce2314000"
        self.o.device_id = "123"

        m.side_effect = ConnectionError()

        self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)

        # No exception thrown, as ConnectionError will be caught


    @requests_mock.Mocker()
    def test_delete_unsynced_record(self, m):
        
        self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)

        self.assertEqual(m.call_count, 0)

if __name__ == "__main__":
    unittest.main()
