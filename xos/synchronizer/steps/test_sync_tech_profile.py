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

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

class TestSyncTechProfile(unittest.TestCase):
    def setUp(self):

        self.mock_etcd = Mock(name="etcd-client")
        etcd = Mock(name="etcd-mocked-lib")
        etcd.client.return_value = self.mock_etcd
        modules = {
            'etcd3': etcd
        }
        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()

        self.sys_path_save = sys.path

        # Setting up the config module
        from xosconfig import Config
        config = os.path.join(test_path, "../test_config.yaml")
        Config.clear()
        Config.init(config, "synchronizer-config-schema.yaml")
        # END Setting up the config module

        from xossynchronizer.mock_modelaccessor_build import mock_modelaccessor_config
        mock_modelaccessor_config(test_path, [("olt-service", "volt.xproto"),
                                                ("rcord", "rcord.xproto")])

        import xossynchronizer.modelaccessor
        reload(xossynchronizer.modelaccessor)      # in case nose2 loaded it in a previous test

        from xossynchronizer.modelaccessor import model_accessor
        self.model_accessor = model_accessor

        from xossynchronizer.modelaccessor import model_accessor
        from sync_tech_profile import SyncTechnologyProfile

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        self.sync_step = SyncTechnologyProfile

        self.o = Mock()
        self.o.technology = "test_technology"
        self.o.profile_id = 64
        self.o.profile_value = '{"test":"profile"}'

        self.o.tologdict.return_value = {'name': "mock-tp"}

    def tearDown(self):
        self.o = None
        sys.path = self.sys_path_save
        self.module_patcher.stop()

    def test_sync(self):

        self.sync_step(model_accessor=self.model_accessor).sync_record(self.o)
        self.mock_etcd.put.assert_called_with('service/voltha/technology_profiles/test_technology/64',
                                              '{"test":"profile"}')

    def test_delete(self):

        self.mock_etcd.get.return_value = [self.o.profile_value, "response from mock-etcd"]

        self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)
        self.mock_etcd.get.assert_called_with('service/voltha/technology_profiles/test_technology/64')
        self.mock_etcd.delete.assert_called_with('service/voltha/technology_profiles/test_technology/64')

    def test_delete_missing_object(self):

        self.mock_etcd.get.return_value = [None, "response from mock-etcd"]

        self.sync_step(model_accessor=self.model_accessor).delete_record(self.o)
        self.mock_etcd.get.assert_called_with('service/voltha/technology_profiles/test_technology/64')
        self.mock_etcd.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
