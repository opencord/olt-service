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
import json

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
        from onu_event import ONUEventStep, model_accessor

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.log = Mock()

        self.event_step = ONUEventStep(self.log)

        self.event = Mock()
        self.event.value = json.dumps({
            'status': 'activate',
            'serial_number': 'BRCM1234',
            'uni_port_of_id': 'of:00100101',
            'of_dpid': 'of:109299321'
        })

        self.onu = Mock()
        self.onu.serial_number = "BRCM1234"
        self.onu.pon_port.olt_device.volt_service.id = 1

        self.service = Mock(id=1)
        self.service.provider_services = []

        self.oss = Mock()
        self.oss.kind = "OSS"
        self.oss.leaf_model = Mock()

    def tearDown(self):
        self.service.provider_services = []

    def test_missing_onu(self):
        with patch.object(ONUDevice.objects, "get_items") as onu_device_mock:
            onu_device_mock.side_effect = IndexError("No ONU")

        with self.assertRaises(Exception) as e:
            self.event_step.process_event(self.event)

        self.assertEqual(e.exception.message, "No ONUDevice with serial_number %s is present in XOS" % self.onu.serial_number)

    def test_do_nothing(self):
        with patch.object(ONUDevice.objects, "get_items") as onu_device_mock , \
            patch.object(Service.objects, "get_items") as service_mock, \
            patch.object(self.log, "info") as logInfo:

            onu_device_mock.return_value = [self.onu]
            service_mock.return_value = [self.service]

            self.event_step.process_event(self.event)

            logInfo.assert_called_with("Not processing events as no OSS service is present (is it a provider of vOLT?")

    def test_call_oss(self):
        self.service.provider_services = [self.oss]

        with patch.object(ONUDevice.objects, "get_items") as onu_device_mock , \
            patch.object(Service.objects, "get_items") as service_mock, \
            patch.object(self.oss.leaf_model, "validate_onu") as validate_onu:

            onu_device_mock.return_value = [self.onu]

            service_mock.return_value = [self.service]

            self.event_step.process_event(self.event)

            validate_onu.assert_called_with(json.loads(self.event.value))
