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
import json
import functools
from mock import patch, call, Mock, PropertyMock
import requests_mock

import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

class TestKubernetesEvent(unittest.TestCase):

    def setUp(self):
        global DeferredException

        self.sys_path_save = sys.path

        config = os.path.join(test_path, "../test_config.yaml")
        from xosconfig import Config
        Config.clear()
        Config.init(config, 'synchronizer-config-schema.yaml')

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("olt-service", "volt.xproto"),
                                                ("rcord", "rcord.xproto"),
                                                ("onos-service", "onos.xproto")])

        import xossynchronizer.modelaccessor
        import mock_modelaccessor
        reload(mock_modelaccessor) # in case nose2 loaded it in a previous test
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        from mock_modelaccessor import MockObjectList

        from kubernetes_event import KubernetesPodDetailsEventStep

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.model_accessor = model_accessor
        self.event_step = KubernetesPodDetailsEventStep

        self.onos = ONOSService(name="myonos",
                                id=1111,
                                rest_hostname = "onos-url",
                                rest_port = "8181",
                                rest_username = "karaf",
                                rest_password = "karaf",
                                backend_code=1,
                                backend_status="succeeded")

        self.fcservice = VOLTService(name="myoltservice",
                                                   id=1112,
                                                   backend_code=1,
                                                   backend_status="succeeded",
                                                    provider_services=[self.onos])

        self.fcsi1 = VOLTServiceInstance(name="myfcsi1",
                                                       owner=self.fcservice,
                                                       backend_code=1,
                                                       backend_status="succeeded")

        self.fcsi2 = VOLTServiceInstance(name="myfcsi2",
                                                       owner=self.fcservice,
                                                       backend_code=1,
                                                       backend_status="succeeded")

        self.fcservice.service_instances = MockObjectList([self.fcsi1, self.fcsi2])

        self.log = Mock()

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_process_event(self):
        with patch.object(VOLTService.objects, "get_items") as fcservice_objects, \
             patch.object(Service.objects, "get_items") as service_objects, \
             patch.object(VOLTServiceInstance, "save", autospec=True) as fcsi_save:
            fcservice_objects.return_value = [self.fcservice]
            service_objects.return_value = [self.onos, self.fcservice]

            event_dict = {"status": "created",
                          "labels": {"xos_service": "myonos"}}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.fcsi1.backend_code, 0)
            self.assertEqual(self.fcsi1.backend_status, "resynchronize due to kubernetes event")

            self.assertEqual(self.fcsi2.backend_code, 0)
            self.assertEqual(self.fcsi2.backend_status, "resynchronize due to kubernetes event")

            fcsi_save.assert_has_calls([call(self.fcsi1, update_fields=["updated", "backend_code", "backend_status"],
                                            always_update_timestamp=True),
                                       call(self.fcsi2, update_fields=["updated", "backend_code", "backend_status"],
                                            always_update_timestamp=True)])

    def test_process_event_unknownstatus(self):
        with patch.object(VOLTService.objects, "get_items") as fcservice_objects, \
             patch.object(Service.objects, "get_items") as service_objects, \
             patch.object(VOLTServiceInstance, "save") as fcsi_save:
            fcservice_objects.return_value = [self.fcservice]
            service_objects.return_value = [self.onos, self.fcservice]

            event_dict = {"status": "something_else",
                          "labels": {"xos_service": "myonos"}}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.fcsi1.backend_code, 1)
            self.assertEqual(self.fcsi1.backend_status, "succeeded")

            self.assertEqual(self.fcsi2.backend_code, 1)
            self.assertEqual(self.fcsi2.backend_status, "succeeded")

            fcsi_save.assert_not_called()

    def test_process_event_unknownservice(self):
        with patch.object(VOLTService.objects, "get_items") as fcservice_objects, \
             patch.object(Service.objects, "get_items") as service_objects, \
             patch.object(VOLTServiceInstance, "save") as fcsi_save:
            fcservice_objects.return_value = [self.fcservice]
            service_objects.return_value = [self.onos, self.fcservice]

            event_dict = {"status": "created",
                          "labels": {"xos_service": "something_else"}}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.fcsi1.backend_code, 1)
            self.assertEqual(self.fcsi1.backend_status, "succeeded")

            self.assertEqual(self.fcsi2.backend_code, 1)
            self.assertEqual(self.fcsi2.backend_status, "succeeded")

            fcsi_save.assert_not_called()

    def test_process_event_nolabels(self):
        with patch.object(VOLTService.objects, "get_items") as fcservice_objects, \
             patch.object(Service.objects, "get_items") as service_objects, \
             patch.object(VOLTServiceInstance, "save") as fcsi_save:
            fcservice_objects.return_value = [self.fcservice]
            service_objects.return_value = [self.onos, self.fcservice]

            event_dict = {"status": "created"}
            event = Mock()
            event.value = json.dumps(event_dict)

            step = self.event_step(model_accessor=self.model_accessor, log=self.log)
            step.process_event(event)

            self.assertEqual(self.fcsi1.backend_code, 1)
            self.assertEqual(self.fcsi1.backend_status, "succeeded")

            self.assertEqual(self.fcsi2.backend_code, 1)
            self.assertEqual(self.fcsi2.backend_status, "succeeded")

            fcsi_save.assert_not_called()

if __name__ == '__main__':
    unittest.main()



