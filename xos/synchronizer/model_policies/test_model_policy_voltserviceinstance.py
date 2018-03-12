
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
import mock

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

        config = os.path.join(test_path, "test_config.yaml")
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
        self.tenant = VOLTServiceInstance(s_tag=111, c_tag=222, service_specific_id=1234)

        self.vsg_service = VSGService(name="the vsg service")

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_handle_create(self):
        with patch.object(VOLTServiceInstancePolicy, "manage_vsg") as manage_vsg, \
                patch.object(VOLTServiceInstancePolicy, "cleanup_orphans") as cleanup_orphans:
            self.policy.handle_create(self.tenant)
            manage_vsg.assert_called_with(self.tenant)
            cleanup_orphans.assert_called_with(self.tenant)

    def test_manage_vsg(self):
        with patch.object(VOLTServiceInstancePolicy, "get_current_vsg") as get_current_vsg, \
                patch.object(VOLTServiceInstancePolicy, "create_eastbound_instance") as create_vsg, \
                patch.object(VSGService.objects, "get_items") as vsg_items:

            vsg_items.return_value = [self.vsg_service]
            get_current_vsg.return_value = None
            self.policy.manage_vsg(self.tenant)

            create_vsg.assert_called()

    def test_get_current_vsg(self):
        with patch.object(ServiceInstanceLink.objects, "get_items") as link_items:
            vsg = VSGServiceInstance()
            link = ServiceInstanceLink(provider_service_instance=vsg, subscriber_service_instance_id=self.tenant.id)

            link_items.return_value = [link]

            vsg = self.policy.get_current_vsg(self.tenant)

            self.assertNotEqual(vsg, None)

    def test_get_current_vsg_noexist(self):
        vsg = self.policy.get_current_vsg(self.tenant)

        self.assertEqual(vsg, None)

    def test_create_vsg(self):
        # with patch.object(model_accessor, "get_model_class") as mock_model_accessor, \
        with patch.object(ServiceInstanceLink, "save", autospec=True) as save_link, \
                patch.object(VSGServiceInstance, "save", autospec=True) as save_vsg:

            # mock_model_accessor.return_value = VSGServiceInstance

            link = Mock()
            link.provider_service.get_service_instance_class_name.return_value = "VSGServiceInstance"

            si = Mock()
            si.creator = 1
            si.subscribed_links.all.return_value = []
            si.owner.subscribed_dependencies.all.return_value = [link]

            self.policy.create_eastbound_instance(si)

            # Should have created a vsg

            self.assertEqual(save_vsg.call_count, 1)
            vsg = save_vsg.call_args[0][0]
            self.assertEqual(vsg.creator, si.creator)

            # Should have created a link from OLT to vsg

            self.assertEqual(save_link.call_count, 1)
            link = save_link.call_args[0][0]
            self.assertEqual(link.provider_service_instance, vsg)
            self.assertEqual(link.subscriber_service_instance, si)

    def test_handle_delete(self):
        self.policy.handle_delete(self.tenant)
        # handle delete does nothing, and should trivially succeed

    def test_cleanup_orphans(self):
        with patch.object(ServiceInstanceLink, "delete", autospec=True) as delete_link, \
                patch.object(VSGServiceInstance.objects, "get_items") as vsg_si_items, \
                patch.object(ServiceInstanceLink.objects, "get_items") as link_items:

            vsg1 = VSGServiceInstance(id=123)
            vsg2 = VSGServiceInstance(id=456)
            link1 = ServiceInstanceLink(provider_service_instance=vsg1, provider_service_instance_id=vsg1.id,
                                        subscriber_service_instance=self.tenant, subscriber_service_instance_id=self.tenant.id)
            link2 = ServiceInstanceLink(provider_service_instance=vsg2, provider_service_instance_id=vsg2.id,
                                        subscriber_service_instance=self.tenant, subscriber_service_instance_id=self.tenant.id)

            self.tenant.subscribed_links=MockObjectList(initial=[link1,link2])

            vsg_si_items.return_value = [vsg1, vsg2]
            link_items.return_value = [link1, link2]

            self.policy.cleanup_orphans(self.tenant)

            # Since there are two VSGs linked to this VOLT, cleanup_orphans() will have caused one of them to be
            # deleted.

            self.assertEqual(delete_link.call_count, 1)

if __name__ == '__main__':
    unittest.main()

