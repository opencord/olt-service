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

import grpc
from voltha_protos.voltha_pb2_grpc import VolthaServiceServicer, add_VolthaServiceServicer_to_server
from voltha_protos.voltha_pb2 import LogicalDevices, Devices, Ports, Device

from google.protobuf import json_format
from google.protobuf.empty_pb2 import Empty

MOCK_VOLTHA_SERVER_ADDRESS = "localhost"
MOCK_VOLTHA_SERVER_PORT = 55555


class VolthaServerMock(VolthaServiceServicer):

    @staticmethod
    def start_voltha_server(grpc_server):
        voltha_server_mock = VolthaServerMock()
        add_VolthaServiceServicer_to_server(voltha_server_mock, grpc_server)
        port_sim = grpc_server.add_insecure_port(MOCK_VOLTHA_SERVER_ADDRESS + ":" + str(MOCK_VOLTHA_SERVER_PORT))
        grpc_server.start()
        return voltha_server_mock, grpc_server, port_sim

    def __init__(self):
        self.disable_called = 0
        self.delete_called = 0
        self.enable_called = 0
        self.fail = False
        self.fail_enable = False
        self.fail_add = False
        self.fail_disable = False
        self.logical_devices = LogicalDevices()
        self.devices = Devices()
        self.created_device = Device()
        self.ports_dict = dict()

    def GetDevice(self, request, context):
        if self.fail:
            context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")
        for item in self.devices.items:
            if item.id == request.id:
                return item
        context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")

    def ListLogicalDevices(self, request, context):
        if self.fail:
            context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")
        return self.logical_devices

    def ListDevices(self, request, context):
        if self.fail:
            context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")
        return self.devices

    def ListDevicePorts(self, request, context):
        empty = {"items": []}
        if self.fail:
            context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")
        return json_format.ParseDict(self.ports_dict.get(request.id, empty), Ports())

    def CreateDevice(self, request, context):
        if self.fail:
            context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")
        if self.fail_add:
            # Any error other than UNAVAILABLE or UNKNOWN
            context.abort(grpc.StatusCode.INTERNAL, "MOCK SERVER ERROR")
        return self.created_device

    def EnableDevice(self, request, context):
        self.enable_called += 1
        if self.fail or self.fail_enable:
            context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")
        return Empty()

    def DisableDevice(self, request, context):
        self.disable_called += 1
        if self.fail or self.fail_disable:
            context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")
        return Empty()

    def DeleteDevice(self, request, context):
        self.delete_called += 1
        if self.fail:
            context.abort(grpc.StatusCode.UNKNOWN, "MOCK SERVER ERROR")
        return Empty()

    def set_logical_devices(self, logical_devices):
        self.logical_devices = json_format.ParseDict(logical_devices, LogicalDevices()) \
            if logical_devices is not None else LogicalDevices()

    def set_devices(self, devices):
        self.devices = json_format.ParseDict(devices, Devices()) if devices is not None else Devices()

    def set_created_device(self, created_device):
        self.created_device = json_format.ParseDict(created_device, Device()) if created_device is not None else Device()

    def set_ports(self, ports):
        self.ports_dict = ports

    def set_fails(self, fail=None, add=None, disable=None, enable=None):
        if fail is not None:
            self.fail = fail
        if enable is not None:
            self.fail_enable = enable
        if add is not None:
            self.fail_add = add
        if enable is not None:
            self.fail_disable = disable
