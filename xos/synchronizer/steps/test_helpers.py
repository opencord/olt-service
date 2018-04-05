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
from helpers import Helpers

class TestHelpers(unittest.TestCase):

    def setUp(self):
        # create a mock service instance
        o = Mock()
        o.voltha_url = "voltha_url"
        o.voltha_user = "voltha_user"
        o.voltha_pass = "voltha_pass"
        o.p_onos_url = "p_onos_url"
        o.p_onos_user = "p_onos_user"
        o.p_onos_pass = "p_onos_pass"

        self.o = o

    def test_format_url(self):
        url = Helpers.format_url("onf.com")
        self.assertEqual(url, "http://onf.com")
        url = Helpers.format_url("http://onf.com")
        self.assertEqual(url, "http://onf.com")

    def test_get_voltha_info(self):
        voltha_dict = Helpers.get_voltha_info(self.o)

        self.assertEqual(voltha_dict["url"], "http://voltha_url")
        self.assertEqual(voltha_dict["user"], "voltha_user")
        self.assertEqual(voltha_dict["pass"], "voltha_pass")

    def test_get_onos_info(self):
        p_onos_dict = Helpers.get_p_onos_info(self.o)

        self.assertEqual(p_onos_dict["url"], "http://p_onos_url")
        self.assertEqual(p_onos_dict["user"], "p_onos_user")
        self.assertEqual(p_onos_dict["pass"], "p_onos_pass")

    def test_datapath_id_to_hex(self):
        hex = Helpers.datapath_id_to_hex(55334486016)
        self.assertEqual(hex, "0000000ce2314000")

        hex = Helpers.datapath_id_to_hex("55334486016")
        self.assertEqual(hex, "0000000ce2314000")

if __name__ == "__main__":
    unittest.main()