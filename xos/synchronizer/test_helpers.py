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

from mock import Mock

from helpers import Helpers


class TestHelpers(unittest.TestCase):

    def setUp(self):
        # create a mock ONOS Service
        onos = Mock()
        onos.name = "ONOS"
        onos.leaf_model.name = "ONOS"
        onos.leaf_model.rest_hostname = "onos_voltha_url"
        onos.leaf_model.rest_port = 4321
        onos.leaf_model.rest_username = "onos_voltha_user"
        onos.leaf_model.rest_password = "onos_voltha_pass"

        # Create a mock service instance
        o = Mock()
        o.voltha_url = "voltha_url"
        o.voltha_port = 1234

        o.provider_services = [onos]

        self.o = o

    def test_format_url(self):
        url = Helpers.format_url("onf.com")
        self.assertEqual(url, "http://onf.com")
        url = Helpers.format_url("http://onf.com")
        self.assertEqual(url, "http://onf.com")

    def test_get_onos_service_name(self):
        name = Helpers.get_onos_service_name(self.o)
        self.assertEqual(name, "ONOS")

    def test_get_voltha_info(self):
        voltha_dict = Helpers.get_voltha_info(self.o)

        self.assertEqual(voltha_dict["url"], "voltha_url")
        self.assertEqual(voltha_dict["port"], 1234)

    def test_get_onos_info(self):
        onos_voltha_dict = Helpers.get_onos_voltha_info(self.o)

        self.assertEqual(onos_voltha_dict["url"], "http://onos_voltha_url")
        self.assertEqual(onos_voltha_dict["port"], 4321)
        self.assertEqual(onos_voltha_dict["user"], "onos_voltha_user")
        self.assertEqual(onos_voltha_dict["pass"], "onos_voltha_pass")

    def test_datapath_id_to_hex(self):
        hex = Helpers.datapath_id_to_hex(55334486016)
        self.assertEqual(hex, "0000000ce2314000")

        hex = Helpers.datapath_id_to_hex("55334486016")
        self.assertEqual(hex, "0000000ce2314000")


if __name__ == "__main__":
    unittest.main()
