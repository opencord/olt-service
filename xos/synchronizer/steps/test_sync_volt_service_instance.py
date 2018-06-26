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

def mock_get_westbound_service_instance_properties(prop):
    return prop

class TestSyncVOLTServiceInstance(unittest.TestCase):
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

        from synchronizers.new_base.syncstep import DeferredException
        from synchronizers.new_base.mock_modelaccessor_build import build_mock_modelaccessor
        # build_mock_modelaccessor(xos_dir, services_dir, [get_models_fn("olt-service", "volt.xproto")])

        # FIXME this is to get jenkins to pass the tests, somehow it is running tests in a different order
        # and apparently it is not overriding the generated model accessor
        build_mock_modelaccessor(xos_dir, services_dir, [get_models_fn("olt-service", "volt.xproto"),
                                                         get_models_fn("vsg", "vsg.xproto"),
                                                         get_models_fn("../profiles/rcord", "rcord.xproto")])
        import synchronizers.new_base.modelaccessor
        from sync_volt_service_instance import SyncVOLTServiceInstance, model_accessor

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = SyncVOLTServiceInstance

        volt_service = Mock()
        volt_service.onos_voltha_url = "onos_voltha_url"
        volt_service.onos_voltha_port = 4321
        volt_service.onos_voltha_user = "onos_voltha_user"
        volt_service.onos_voltha_pass = "onos_voltha_pass"

        si = Mock()
        si.get_westbound_service_instance_properties = mock_get_westbound_service_instance_properties

        uni_port = Mock()
        uni_port.port_no = "uni_port_id"

        onu_device = Mock()
        onu_device.name = "BRCM1234"
        onu_device.pon_port.olt_device.dp_id = None
        onu_device.pon_port.olt_device.name = "Test OLT Device"
        onu_device.uni_ports.first.return_value = uni_port

        # create a mock service instance
        o = Mock()
        o.id = 1
        o.owner_id = "volt_service"
        o.onu_device = onu_device
        o.tologdict.return_value = {}

        self.o = o
        self.si = si
        self.onu_device = onu_device
        self.volt_service = volt_service

    def tearDown(self):
        self.o = None
        sys.path = self.sys_path_save

    @requests_mock.Mocker()
    def test_do_not_sync(self, m):
        self.onu_device.pon_port.olt_device.dp_id = None

        with patch.object(ServiceInstance.objects, "get") as service_instance_mock, \
                patch.object(VOLTService.objects, "get") as olt_service_mock:
            service_instance_mock.return_value = self.si
            olt_service_mock.return_value = self.volt_service

            with self.assertRaises(DeferredException) as e:
                self.sync_step().sync_record(self.o)

            self.assertFalse(m.called)
            self.assertEqual(e.exception.message, "Waiting for OLTDevice Test OLT Device to be synchronized")

    @requests_mock.Mocker()
    def test_do_sync(self, m):
        m.post("http://onos_voltha_url:4321/onos/olt/oltapp/of:dp_id/uni_port_id/c_tag", status_code=200, json={})

        self.onu_device.pon_port.olt_device.dp_id = "of:dp_id"

        with patch.object(ServiceInstance.objects, "get") as service_instance_mock, \
                patch.object(VOLTService.objects, "get") as olt_service_mock:
            service_instance_mock.return_value = self.si
            olt_service_mock.return_value = self.volt_service

            self.sync_step().sync_record(self.o)
            self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_do_sync_fail(self, m):
        m.post("http://onos_voltha_url:4321/onos/olt/oltapp/of:dp_id/uni_port_id/c_tag", status_code=500, text="Mock Error")

        self.onu_device.pon_port.olt_device.dp_id = "of:dp_id"

        with patch.object(ServiceInstance.objects, "get") as service_instance_mock, \
                patch.object(VOLTService.objects, "get") as olt_service_mock:
            service_instance_mock.return_value = self.si
            olt_service_mock.return_value = self.volt_service

            with self.assertRaises(Exception) as e:
                self.sync_step().sync_record(self.o)
                self.assertTrue(m.called)
                self.assertEqual(e.exception.message, "Failed to add subscriber in onos voltha: Mock Error")

    @requests_mock.Mocker()
    def test_delete(self, m):
        m.delete("http://onos_voltha_url:4321/onos/olt/oltapp/of:dp_id/uni_port_id", status_code=204)

        self.onu_device.pon_port.olt_device.dp_id = "of:dp_id"

        with patch.object(VOLTService.objects, "get") as olt_service_mock:
            olt_service_mock.return_value = self.volt_service

            self.sync_step().delete_record(self.o)
            self.assertTrue(m.called)
            self.assertEqual(m.call_count, 1)

if __name__ == "__main__":
    unittest.main()
