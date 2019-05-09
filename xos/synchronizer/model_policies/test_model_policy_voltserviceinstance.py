
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

class TestModelPolicyVOLTServiceInstance(unittest.TestCase):
    def setUp(self):
        global VOLTServiceInstancePolicy, MockObjectList

        self.sys_path_save = sys.path

        config = os.path.join(test_path, "../test_config.yaml")
        from xosconfig import Config
        Config.clear()
        Config.init(config, 'synchronizer-config-schema.yaml')

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("olt-service", "volt.xproto"),
                                                ("rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from mock_modelaccessor import MockObjectList
        from model_policy_voltserviceinstance import VOLTServiceInstancePolicy

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        # Some of the functions we call have side-effects. For example, creating a ServiceInstance may lead to creation of
        # tags. Ideally, this wouldn't happen, but it does. So make sure we reset the world.
        model_accessor.reset_all_object_stores()

        self.policy = VOLTServiceInstancePolicy(model_accessor=self.model_accessor)
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
            patch.object(ServiceInstance, "save", autospec=True) as save_vsg:

            subscriber_si = Mock()

            link = Mock()
            link.provider_service.get_service_instance_class_name.return_value = "ServiceInstance"
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
            patch.object(ServiceInstance, "save", autospec=True) as save_vsg:

            subscriber_si = Mock()

            link = Mock()
            link.provider_service.get_service_instance_class_name.return_value = "ServiceInstance"
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
            self.si.save_changed_fields.assert_called()

    def test_handle_delete(self):
        self.policy.handle_delete(self.si)
        # handle delete does nothing, and should trivially succeed


if __name__ == '__main__':
    unittest.main()
