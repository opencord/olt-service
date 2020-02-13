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

from concurrent.futures import ThreadPoolExecutor
import unittest
import functools
from mock import patch, call, Mock, PropertyMock
import requests_mock
import grpc
import os, sys

test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mock_voltha_server import VolthaServerMock, MOCK_VOLTHA_SERVER_ADDRESS, MOCK_VOLTHA_SERVER_PORT
from voltha_client import clear_voltha_client_cache


def match_json(desired, req):
    if desired != req.json():
        raise Exception("Got request %s, but body is not matching" % req.url)
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
        reload(xossynchronizer.modelaccessor)  # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        from sync_olt_device import SyncOLTDevice, DeferredException
        self.sync_step = SyncOLTDevice

        pon_port = Mock()
        pon_port.port_id = "00ff00"

        # create a mock ONOS Service
        onos = Mock()
        onos.name = "ONOS"
        onos.leaf_model.rest_hostname = "onos"
        onos.leaf_model.rest_port = 4321
        onos.leaf_model.rest_username = "karaf"
        onos.leaf_model.rest_password = "karaf"

        # Create a mock OLTDevice
        o = Mock()
        o.volt_service.voltha_url = MOCK_VOLTHA_SERVER_ADDRESS
        o.volt_service.voltha_port = MOCK_VOLTHA_SERVER_PORT

        clear_voltha_client_cache()
        self.server = grpc.server(ThreadPoolExecutor(max_workers=5))
        self.voltha_mock, _, _ = VolthaServerMock.start_voltha_server(self.server)

        o.volt_service.provider_services = [onos]

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
        o.serial_number = None
        o.of_id = None
        o.id = 1

        o.tologdict.return_value = {'name': "Mock VOLTServiceInstance"}

        o.save_changed_fields.return_value = "Saved"

        o.pon_ports.all.return_value = [pon_port]

        self.o = o

        self.voltha_devices_response = {"id": "123", "serial_number": "foobar"}

        self.tp = TechnologyProfile(
            technology="xgspon",
            profile_id=64,
            profile_value="{}"
        )

    def tearDown(self):
        self.server.stop(None)
        self.o = None
        sys.path = self.sys_path_save

    def test_get_of_id_from_device(self):
        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
                {"root_device_id": "0001cc4974a62b87", "id": "0001000000000001"}
            ]
        }
        self.voltha_mock.set_logical_devices(logical_devices)
        self.o.device_id = "123"
        self.o = self.sync_step.get_ids_from_logical_device(self.o)
        self.assertEqual(self.o.of_id, "0001000ce2314000")
        self.assertEqual(self.o.dp_id, "of:0000000ce2314000")

        with self.assertRaises(Exception) as e:
            self.o.device_id = "idonotexist"
            self.sync_step.get_ids_from_logical_device(self.o)
        self.assertEqual(e.exception.message, "Can't find a logical_device for OLT device id: idonotexist")

    def test_sync_record_fail_add(self):
        """
        Should print an error if we can't add the device in VOLTHA
        """
        with self.assertRaises(Exception) as e, \
                patch.object(TechnologyProfile.objects, "get") as tp_mock:
            tp_mock.return_value = self.tp
            self.voltha_mock.set_fails(add=True)

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        self.assertEqual(e.exception.message,
                         'Failed to add OLT device: type: "ponsim_olt"\nhost_and_port: "172.17.0.1:50060"\n, (StatusCode.INTERNAL, MOCK SERVER ERROR)')

    def test_sync_record_fail_no_id(self):
        """
        Should print an error if VOLTHA does not return the device id
        """
        created_device_no_id = {
            "id": "",
            "type": "simulated_olt",
            "host_and_port": "172.17.0.1:50060",
            "admin_state": "ENABLED",
            "oper_status": "ACTIVE",
            "serial_number": "serial_number",
        }

        with self.assertRaises(Exception) as e, \
                patch.object(TechnologyProfile.objects, "get") as tp_mock:
            tp_mock.return_value = self.tp
            self.voltha_mock.set_created_device(created_device_no_id)

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        self.assertEqual(e.exception.message,
                         "VOLTHA Device Id is empty. This probably means that the OLT device is already provisioned in VOLTHA")

    def test_sync_record_fail_enable(self):
        """
        Should print an error if device.enable fails
        """

        with self.assertRaises(Exception) as e, \
                patch.object(TechnologyProfile.objects, "get") as tp_mock:
            tp_mock.return_value = self.tp
            self.voltha_mock.set_created_device(self.voltha_devices_response)
            self.voltha_mock.set_fails(enable=True)

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        self.assertEqual(e.exception.message,
                         "[OLT enable] Failed to enable device in VOLTHA: 123 (StatusCode.UNKNOWN, MOCK SERVER ERROR)")

    @requests_mock.Mocker()
    def test_sync_record_success(self, m):
        """
        If device.enable succeed should fetch the state, retrieve the of_id and push it to ONOS
        """
        self.voltha_devices_response.update({
            "type": self.o.device_type,
            "host_and_port": "%s:%s" % (self.o.host, self.o.port)
        })

        devices = {"items": [
            {
                "id": "123",
                "oper_status": "ACTIVE",
                "admin_state": "ENABLED",
                "serial_number": "foobar"
            }
        ]}

        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
            ]
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

        with patch.object(TechnologyProfile.objects, "get") as tp_mock:
            self.voltha_mock.set_logical_devices(logical_devices)
            self.voltha_mock.set_devices(devices)
            self.voltha_mock.set_created_device(self.voltha_devices_response)
            tp_mock.return_value = self.tp
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

        self.voltha_devices_response.update({
            "type": self.o.device_type,
            "mac_address": self.o.mac_address
        })

        onos_expected_conf = {
            "devices": {
                "of:0000000ce2314000": {
                    "basic": {
                        "name": self.o.name
                    }
                }
            }
        }
        devices = {"items": [
            {
                "id": "123",
                "oper_status": "ACTIVE",
                "admin_state": "ENABLED",
                "serial_number": "foobar"
            }
        ]}
        m.post("http://onos:4321/onos/v1/network/configuration/", status_code=200, json=onos_expected_conf,
               additional_matcher=functools.partial(match_json, onos_expected_conf))

        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
                {"root_device_id": "0001cc4974a62b87", "id": "0001000000000001"}
            ]
        }

        with patch.object(TechnologyProfile.objects, "get") as tp_mock:
            tp_mock.return_value = self.tp
            self.voltha_mock.set_logical_devices(logical_devices)
            self.voltha_mock.set_devices(devices)
            self.voltha_mock.set_created_device(self.voltha_devices_response)

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
            self.assertEqual(self.o.admin_state, "ENABLED")
            self.assertEqual(self.o.oper_status, "ACTIVE")
            self.assertEqual(self.o.of_id, "0001000ce2314000")

            # One save during preprovision
            # One save during activation to set backend_status to "Waiting for device to activate"
            # One save after activation has succeeded
            self.assertEqual(self.o.save_changed_fields.call_count, 3)

    def test_sync_record_enable_timeout(self):
        """
        If device activation fails we need to tell the user.

        OLT will be preprovisioned.
        OLT will return "ERROR" for oper_status during activate and will eventually exceed retries.s
        """

        self.voltha_devices_response.update({
            "type": self.o.device_type,
            "host_and_port": "%s:%s" % (self.o.host, self.o.port)
        })

        devices = {"items": [
            {
                "id": "123",
                "oper_status": "FAILED",
                "admin_state": "ENABLED",
                "serial_number": "foobar"
            }
        ]}

        logical_devices = {
            "items": [
                {"root_device_id": "123", "id": "0001000ce2314000", "datapath_id": "55334486016"},
                {"root_device_id": "0001cc4974a62b87", "id": "0001000000000001"}
            ]
        }

        with self.assertRaises(Exception) as e, \
                patch.object(TechnologyProfile.objects, "get") as tp_mock:
            tp_mock.return_value = self.tp
            self.voltha_mock.set_logical_devices(logical_devices)
            self.voltha_mock.set_devices(devices)
            self.voltha_mock.set_created_device(self.voltha_devices_response)

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        self.assertEqual(e.exception.message, "It was not possible to activate OLTDevice with id 1")
        self.assertEqual(self.o.oper_status, "FAILED")
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

        with patch.object(TechnologyProfile.objects, "get") as tp_mock:
            tp_mock.return_value = self.tp

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
            self.o.save.assert_not_called()
            self.o.save_changed_fields.assert_not_called()

    def test_sync_record_deactivate(self):
        """
        If device.admin_state == "DISABLED" and oper_status == "ACTIVE", then OLT should be deactivated.
        """

        self.voltha_devices_response.update({
            "type": self.o.device_type,
            "host_and_port": "%s:%s" % (self.o.host, self.o.port)
        })

        # Make it look like we have an active OLT that we are deactivating.
        self.o.admin_state = "DISABLED"
        self.o.oper_status = "ACTIVE"
        self.o.serial_number = "foobar"
        self.o.device_id = "123"
        self.o.of_id = "0001000ce2314000"

        with patch.object(TechnologyProfile.objects, "get") as tp_mock:
            tp_mock.return_value = self.tp
            self.voltha_mock.set_created_device(self.voltha_devices_response)

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

            # No saves as state has not changed (will eventually be saved
            # by the synchronizer framework to update backend_status)
            self.assertEqual(self.o.save.call_count, 0)
            self.assertEqual(self.o.save_changed_fields.call_count, 0)

            # Make sure disable was called
            self.assertEqual(self.voltha_mock.disable_called, 1)

    @requests_mock.Mocker()
    def test_sync_record_deactivate_already_inactive(self, m):
        """
        If device.admin_state == "DISABLED" and device.oper_status == "UNKNOWN", then the device is already deactivated
        and VOLTHA should not be called.
        """

        self.voltha_devices_response.update({
            "type": self.o.device_type,
            "host_and_port": "%s:%s" % (self.o.host, self.o.port)
        })

        # Make it look like we have an active OLT that we are deactivating.
        self.o.admin_state = "DISABLED"
        self.o.oper_status = "UNKNOWN"
        self.o.serial_number = "foobar"
        self.o.device_id = "123"
        self.o.of_id = "0001000ce2314000"

        with patch.object(TechnologyProfile.objects, "get") as tp_mock:
            tp_mock.return_value = self.tp

            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
            self.voltha_mock.set_created_device(self.voltha_devices_response)

            # No saves as state has not changed (will eventually be saved by synchronizer framework
            # to update backend_status)
            self.assertEqual(self.o.save.call_count, 0)
            self.assertEqual(self.o.save_changed_fields.call_count, 0)

    def test_do_not_sync_without_tech_profile(self):
        self.o.technology = "xgspon"
        with self.assertRaises(DeferredException) as e:
            self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)

        self.assertEqual(e.exception.message, "Waiting for a TechnologyProfile (technology=xgspon) to be synchronized")

    def test_delete_record(self):
        self.o.of_id = "0001000ce2314000"
        self.o.device_id = "123"

        self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)

        self.assertEqual(self.voltha_mock.disable_called + self.voltha_mock.delete_called, 2)

    def test_delete_record_connectionerror(self):
        self.o.of_id = "0001000ce2314000"
        self.o.device_id = "123"
        self.server.stop(None)

        self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)

        # No exception thrown, as ConnectionError will be caught
        self.assertEqual(self.voltha_mock.disable_called + self.voltha_mock.delete_called, 0)

    def test_delete_unsynced_record(self):
        # voltha_server_mock, _, _ = VolthaServerMock.start_voltha_server(self.server)
        self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)

        self.assertEqual(self.voltha_mock.disable_called + self.voltha_mock.delete_called, 0)


if __name__ == "__main__":
    unittest.main()
