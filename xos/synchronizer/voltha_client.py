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

from voltha_protos.voltha_pb2_grpc import VolthaServiceStub
from google.protobuf.empty_pb2 import Empty
from voltha_protos.voltha_pb2 import ID, Device

TIMEOUT = 10  # type: int

# Map to cache voltha channels, indexed by URL and port (NOTE: timeout can change between different usage)
voltha_clients = {}


def get_voltha_client(olt_service, timeout=TIMEOUT):
    """
    Query the local voltha client cache.
    Override the timeout of the cached client if any.

    :param olt_service: The v-olt service instance
    :param timeout: gRPC timeout
    :return: The cached client if present, otherwise a new instance of VolthaClient
    """
    # Query cache, otherwise create new instance
    client = voltha_clients.get((olt_service.voltha_url, olt_service.voltha_port),
                                VolthaClient(olt_service.voltha_url, olt_service.voltha_port, timeout))
    client._timeout = timeout
    voltha_clients[(olt_service.voltha_url, olt_service.voltha_port)] = client
    return client


def clear_voltha_client_cache():
    # Useful for testing purposes
    voltha_clients.clear()


class VolthaClient(object):
    """
    VOLTHA gRPC client
    """

    def __init__(self, url, port, timeout=TIMEOUT):
        self.voltha_url = url
        self.voltha_port = port
        self.channel = None
        self._timeout = timeout  # gRPC timeout [s]

    def open_channel(self):
        """
        Open gRPC channel with VOLTHA
        :return: True if channel is opened, False if it was already opened
        """
        if self.channel is None:
            self.channel = grpc.insecure_channel(self.voltha_url + ":" + str(self.voltha_port))
            return True
        return False

    def close_channel(self):
        """
        Close the gRPC channel
        :return:
        """
        if self.channel is not None:
            self.channel.close()
            self.channel = None

    def list_devices(self):
        """
        :return: list of devices
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        try:
            devs = self._get_stub().ListDevices(Empty(), timeout=self._timeout)
            return devs.items
        except grpc.RpcError as e:
            self._manage_std_conn_error(e)
            raise VolthaException("Failed to retrieve devices from VOLTHA (%s, %s)" % (e.code(), e.details()))

    def list_olt_devices(self):
        """
        :return: list of OLT devices
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        devices = self.list_devices()
        return [d for d in devices if "olt" in d.type]

    def list_onu_devices(self):
        """
        :return: list of ONU devices
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        devices = self.list_devices()
        return [d for d in devices if "onu" in d.type]

    def list_device_ports(self, device_id):
        """
        Return the list of ports of the given device ID.

        :param device_id: The given device ID
        :return: list of ports of the given device ID
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        dev_id = ID(id=device_id)
        try:
            ports = self._get_stub().ListDevicePorts(dev_id, timeout=self._timeout)
            return ports.items
        except grpc.RpcError as e:
            self._manage_std_conn_error(e)
            raise VolthaException(
                "Failed to retrieve port from VOLTHA for %s (%s, %s)" % (device_id, e.code(), e.details()))

    def list_logical_devices(self):
        """
        Return the list of logical devices.
        :return: list of logical devices as exposed by VOLTHA
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        try:
            devs = self._get_stub().ListLogicalDevices(Empty(), timeout=self._timeout)
            return devs.items
        except grpc.RpcError as e:
            self._manage_std_conn_error(e)
            raise VolthaException("Failed to retrieve logical devices from VOLTHA (%s, %s)" % (e.code(), e.details()))

    def create_olt_device(self, olt_xos_model):
        """
        Create a new OLT device in VOLTHA. The response will contain the ID of the created device,
        this field will be blank if the device has been already pre-provisioned.

        :param olt_xos_model: The OLT xos model
        :return: the created device in VOLTHA
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        new_olt_dev = Device()
        new_olt_dev.type = olt_xos_model.device_type

        if hasattr(olt_xos_model, "host") and hasattr(olt_xos_model, "port"):
            new_olt_dev.host_and_port = "%s:%s" % (olt_xos_model.host, olt_xos_model.port)
        elif hasattr(olt_xos_model, "mac_address"):
            new_olt_dev.mac_address = olt_xos_model.mac_address

        try:
            resp_dev = self._get_stub().CreateDevice(new_olt_dev, timeout=self._timeout)
            return resp_dev
        except grpc.RpcError as e:
            self._manage_std_conn_error(e)
            if grpc.StatusCode.UNKNOWN == e.code():
                # FIXME: what is voltha returning for already pre-provisioned OLT devices?
                #  maybe grcp.StatusCode.ALREADY_EXISTS?
                return new_olt_dev
            raise VolthaException("Failed to add OLT device: %s, (%s, %s)" % (new_olt_dev, e.code(), e.details()))

    def enable_device(self, device_id):
        """
        :param device_id:
        :return
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        dev_id = ID(id=device_id)
        try:
            self._get_stub().EnableDevice(dev_id, timeout=self._timeout)
        except grpc.RpcError as e:
            self._manage_std_conn_error(e)
            raise VolthaException("Failed to enable device in VOLTHA: %s (%s, %s)" % (device_id, e.code(), e.details()))

    def disable_device(self, device_id):
        """
        :param device_id:
        :return:
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        dev_id = ID(id=device_id)
        try:
            self._get_stub().DisableDevice(dev_id, timeout=self._timeout)
        except grpc.RpcError as e:
            self._manage_std_conn_error(e)
            raise Exception("Failed to disable device in VOLTHA: %s, (%s, %s)" % (device_id, e.code(), e.details()))

    def delete_device(self, device_id):
        """

        :param device_id:
        :return:
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        dev_id = ID(id=device_id)
        try:
            self._get_stub().DeleteDevice(dev_id, timeout=self._timeout)
        except grpc.RpcError as e:
            self._manage_std_conn_error(e)
            raise Exception("Failed to delete device in VOLTHA: %s (%s, %s)" % (device_id, e.code(), e.details()))

    def get_device(self, device_id):
        """

        :param device_id:
        :return:
        :except: ConnectionException if VOLTHA is unreachable, otherwise VolthaException if any other RpcError
        """
        dev_id = ID(id=device_id)
        try:
            dev = self._get_stub().GetDevice(dev_id, timeout=self._timeout)
            return dev
        except grpc.RpcError as e:
            self._manage_std_conn_error(e)
            raise VolthaException(
                "Failed to get device information from VOLTHA: %s (%s, %s)" % (device_id, e.code(), e.details()))

    @staticmethod
    def _manage_std_conn_error(e):
        if grpc.StatusCode.UNAVAILABLE == e.code():
            raise ConnectionError("It was not possible to connect to VOLTHA, " \
                                 "either VOLTHA is offline or URL is invalid(%s %s)" % (e.code(), e.details()))
        if grpc.StatusCode.DEADLINE_EXCEEDED == e.code():
            raise ConnectionError("Failed to contact VOLTHA (%s %s)" % (e.code(), e.details()))

    def _get_stub(self):
        self.open_channel()
        return VolthaServiceStub(self.channel)

    def __del__(self):
        self.close_channel()


class ConnectionError(Exception):
    pass


class VolthaException(Exception):
    pass

