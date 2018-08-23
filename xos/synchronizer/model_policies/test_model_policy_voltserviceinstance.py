
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

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
service_dir=os.path.join(test_path, "../../../..")
xos_dir=os.path.join(test_path, "../../..")
if not os.path.exists(os.path.join(test_path, "new_base")):
    xos_dir=os.path.join(test_path, "../../../../../../orchestration/xos/xos")
    services_dir=os.path.join(xos_dir, "../../xos_services")

# While transitioning from static to dynamic load, the path to find neighboring xproto files has changed. So check
# both possible locations...
def get_models_fn(service_name, xproto_name):
    name = os.path.join(service_name, "xos", xproto_name)
    if os.path.exists(os.path.join(services_dir, name)):
        return name
    else:
        name = os.path.join(service_name, "xos", "synchronizer", "models", xproto_name)
        if os.path.exists(os.path.join(services_dir, name)):
            return name
    raise Exception("Unable to find service=%s xproto=%s" % (service_name, xproto_name))

class TestModelPolicyVOLTServiceInstance(unittest.TestCase):
    def setUp(self):
        global VOLTServiceInstancePolicy, MockObjectList

        self.sys_path_save = sys.path
        sys.path.append(xos_dir)
        sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))

        config = os.path.join(test_path, "../test_config.yaml")
        from xosconfig import Config
        Config.clear()
        Config.init(config, 'synchronizer-config-schema.yaml')

        from synchronizers.new_base.mock_modelaccessor_build import build_mock_modelaccessor
        build_mock_modelaccessor(xos_dir, services_dir, [get_models_fn("olt-service", "volt.xproto"),
                                                         get_models_fn("vsg", "vsg.xproto"),
                                                         get_models_fn("../profiles/rcord", "rcord.xproto")])

        import synchronizers.new_base.modelaccessor
        import model_policy_voltserviceinstance
        from model_policy_voltserviceinstance import VOLTServiceInstancePolicy, model_accessor

        from mock_modelaccessor import MockObjectList

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        # Some of the functions we call have side-effects. For example, creating a VSGServiceInstance may lead to creation of
        # tags. Ideally, this wouldn't happen, but it does. So make sure we reset the world.
        model_accessor.reset_all_object_stores()

        self.policy = VOLTServiceInstancePolicy()
        self.si = Mock()

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_handle_create(self):
        with patch.object(VOLTServiceInstancePolicy, "create_eastbound_instance") as create_eastbound_instance, \
            patch.object(VOLTServiceInstancePolicy, "associate_onu_device") as associate_onu_device:

            self.policy.handle_create(self.si)
            create_eastbound_instance.assert_called_with(self.si)
            associate_onu_device.assert_called_with(self.si)

    def test_create_vsg(self):
        with patch.object(ServiceInstanceLink, "save", autospec=True) as save_link, \
            patch.object(VSGServiceInstance, "save", autospec=True) as save_vsg:

            subscriber_si = Mock()

            link = Mock()
            link.provider_service.get_service_instance_class_name.return_value = "VSGServiceInstance"
            link.provider_service.name = "FabricCrossconnect"
            link.provider_service.validate_links = Mock(return_value=[])
            link.provider_service.acquire_service_instance = Mock(return_value=subscriber_si)
            link.provider_service.leaf_model = link.provider_service

            si = Mock()
            si.subscribed_links.all.return_value = []
            si.owner.subscribed_dependencies.all.return_value = [link]

            self.policy.create_eastbound_instance(si)

            link.provider_service.validate_links.assert_called_with(si)
            link.provider_service.acquire_service_instance.assert_called_with(si)

    def test_create_vsg_already_exists(self):
        with patch.object(ServiceInstanceLink, "save", autospec=True) as save_link, \
            patch.object(VSGServiceInstance, "save", autospec=True) as save_vsg:

            subscriber_si = Mock()

            link = Mock()
            link.provider_service.get_service_instance_class_name.return_value = "VSGServiceInstance"
            link.provider_service.name = "FabricCrossconnect"
            link.provider_service.validate_links = Mock(return_value=subscriber_si)
            link.provider_service.acquire_service_instance = Mock()
            link.provider_service.leaf_model = link.provider_service

            si = Mock()
            si.subscribed_links.all.return_value = []
            si.owner.subscribed_dependencies.all.return_value = [link]

            self.policy.create_eastbound_instance(si)

            link.provider_service.validate_links.assert_called_with(si)
            link.provider_service.acquire_service_instance.assert_not_called()

    def test_associate_onu(self):
        with patch.object(ServiceInstance.objects, "get") as get_si, \
            patch.object(ONUDevice.objects, "get") as get_onu:

            mock_si = Mock()
            mock_si.get_westbound_service_instance_properties.return_value = "BRCM1234"
            get_si.return_value = mock_si

            mock_onu = Mock()
            mock_onu.id = 12
            get_onu.return_value = mock_onu

            self.policy.associate_onu_device(self.si)

            self.assertEqual(self.si.onu_device_id, mock_onu.id)
            self.si.save.assert_called()

    def test_handle_delete(self):
        self.policy.handle_delete(self.si)
        # handle delete does nothing, and should trivially succeed

if __name__ == '__main__':
    unittest.main()

