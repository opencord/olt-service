# Copyright 2020-present Open Networking Foundation
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
from time import sleep

import grpc
import os
from concurrent.futures import ThreadPoolExecutor

from voltha_client import VolthaClient, ConnectionError
from mock_voltha_server import VolthaServerMock, MOCK_VOLTHA_SERVER_ADDRESS, MOCK_VOLTHA_SERVER_PORT
from google.protobuf import json_format

test_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

class TestVolthaClient(unittest.TestCase):

    def setUp(self):
        self.server = grpc.server(ThreadPoolExecutor(max_workers=5))
        self.voltha_server_mock, _, _ = VolthaServerMock.start_voltha_server(self.server)
        self.voltha_client = VolthaClient(url=MOCK_VOLTHA_SERVER_ADDRESS, port=MOCK_VOLTHA_SERVER_PORT, timeout=1)
        self.devices = {"items": []}
        self.olts = [
            {
                "id": "test_id",
                "type": "simulated_olt",
            },
            {
                'id': 'tibit_id',
                'type': 'tibit_olt',
            }
        ]

        self.onus = [
            {
                "id": "1",
                "type": "onu",
            },
            {
                "id": "2",
                "type": "broadcom_onu",
            }
        ]
        self.devices["items"].extend(self.olts)
        self.devices["items"].extend(self.onus)
        # Need to wait an be sure the gRPC voltha mock server is up and running
        # before running the actual test.
        for i in range(5):
            try:
                self.voltha_client.list_devices()
                return
            except ConnectionError:
                sleep(1)
        self.fail("VOLTHA gRPC server failed to start!")

    def tearDown(self):
        self.voltha_client.close_channel()
        self.server.stop(None)

    def test_list_olt_devices(self):
        self.voltha_server_mock.set_devices(self.devices)
        print(self.voltha_server_mock.devices)
        olts = self.voltha_client.list_olt_devices()

        self.assertEqual(self.olts, [json_format.MessageToDict(o) for o in olts])

    def test_list_olt_devices_nodevices(self):
        olts = self.voltha_client.list_olt_devices()

        self.assertEqual(len(olts), 0)

    def test_list_onu_devices(self):
        self.voltha_server_mock.set_devices(self.devices)
        onus = self.voltha_client.list_onu_devices()

        self.assertEqual(self.onus, [json_format.MessageToDict(o) for o in onus])

    def test_list_onu_devices_nodevices(self):
        onus = self.voltha_client.list_olt_devices()

        self.assertEqual(len(onus), 0)


if __name__ == "__main__":
    unittest.main()
