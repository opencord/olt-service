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

class TestSyncVOLTServiceInstance(unittest.TestCase):
    def setUp(self):

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
        self.sync_step().sync_record(self.o)
        self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_disable(self, m):
        m.post("http://voltha_url:1234/api/v1/devices/test_id/disable")

        self.o.admin_state = "DISABLED"
        self.sync_step().sync_record(self.o)
        self.assertTrue(m.called)

    @requests_mock.Mocker()
    def test_disable_fail(self, m):
        m.post("http://voltha_url:1234/api/v1/devices/test_id/disable", status_code=500, text="Mock Error")

        self.o.admin_state = "DISABLED"

        with self.assertRaises(Exception) as e:
            self.sync_step().sync_record(self.o)
            self.assertTrue(m.called)
            self.assertEqual(e.exception.message, "Failed to disable ONU device: Mock Error")

if __name__ == "__main__":
    unittest.main()
