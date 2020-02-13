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

from xossynchronizer.pull_steps.pullstep import PullStep
from xossynchronizer.modelaccessor import ONUDevice, VOLTService, OLTDevice, PONPort, ANIPort, UNIPort

from xosconfig import Config
from multistructlog import create_logger

from voltha_protos.common_pb2 import OperStatus, AdminState, ConnectStatus
from voltha_protos.voltha_pb2 import Port

import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from voltha_client import get_voltha_client

log = create_logger(Config().get('logging'))


class ONUDevicePullStep(PullStep):
    def __init__(self, model_accessor):
        super(ONUDevicePullStep, self).__init__(model_accessor=model_accessor, observed_model=ONUDevice)

    def pull_records(self):
        log.debug("[ONU pull step] pulling ONU devices from VOLTHA")

        try:
            self.volt_service = VOLTService.objects.all()[0]
        except IndexError:
            log.warn('VOLTService not found')
            return
        try:
            onu_devices = get_voltha_client(self.volt_service).list_onu_devices()
            if onu_devices is None:
                return
            if len(onu_devices) > 0:
                log.debug("received devices", onus=onu_devices)
                onus_in_voltha = self.create_or_update_onus(onu_devices)

                # TODO
                # [ ] delete ONUS as ONUDevice.objects.all() - updated ONUs
            else:
                log.debug("[ONU pull step] Blank response received")
        except Exception as e:
            log.error("[ONU pull step] " + e.message)
            return

    def create_or_update_onus(self, onus):

        updated_onus = []

        for onu in onus:
            try:
                model = ONUDevice.objects.filter(serial_number=onu.serial_number)[0]
                log.debug("[ONU pull step] ONUDevice already exists, updating it", serial_number=onu.serial_number)
            except IndexError:
                model = ONUDevice()
                model.serial_number = onu.serial_number
                model.admin_state = AdminState.Types.Name(onu.admin_state)

                log.debug("[ONU pull step] ONUDevice is new, creating it", serial_number=onu.serial_number, admin_state=onu.admin_state)

            try:
                olt = OLTDevice.objects.get(device_id=onu.parent_id)
            except IndexError:
                log.warning("[ONU pull step] Unable to find OLT for ONUDevice", serial_number=onu.serial_number, olt_device_id=onu.parent_id)
                continue

            try:
                pon_port = PONPort.objects.get(port_no=onu.parent_port_no, olt_device_id=olt.id)
            except IndexError:
                log.warning("[ONU pull step] Unable to find pon_port for ONUDevice", serial_number=onu.serial_number, olt_device_id=onu.parent_id, port_no=onu.parent_port_no)
                continue

            # Adding feedback state to the device
            model.vendor = onu.vendor
            model.device_type = onu.type
            model.device_id = onu.id

            model.oper_status = OperStatus.Types.Name(onu.oper_status)
            model.connect_status = ConnectStatus.Types.Name(onu.connect_status)
            model.reason = onu.reason
            model.xos_managed = False

            model.pon_port = pon_port
            model.pon_port_id = pon_port.id

            model.save_changed_fields()

            self.fetch_onu_ports(model)

            updated_onus.append(model)

        return updated_onus

    def fetch_onu_ports(self, onu):
        try:
            onu_ports = get_voltha_client(self.volt_service).list_device_ports(onu.device_id)
            if onu_ports is None:
                return
            log.debug("[ONU pull step] received ports", ports=onu_ports, onu=onu.device_id)
            self.create_or_update_ports(onu_ports, onu)
        except Exception as e:
            log.error("[ONU pull step] " + e.message)
            return

    def create_or_update_ports(self, ports, onu):
        uni_ports = [p for p in ports if Port.PortType.Name(p.type) == "ETHERNET_UNI"]
        pon_onu_ports = [p for p in ports if Port.PortType.Name(p.type) == "PON_ONU"]

        self.create_or_update_uni_port(uni_ports, onu)
        self.create_or_update_ani_port(pon_onu_ports, onu)

    def create_or_update_uni_port(self, uni_ports, onu):
        update_ports = []

        for port in uni_ports:
            try:
                model = UNIPort.objects.filter(port_no=port.port_no, onu_device_id=onu.id)[0]
                log.debug("[ONU pull step] UNIPort already exists, updating it", port_no=port.port_no, onu_device_id=onu.id)
            except IndexError:
                model = UNIPort()
                model.port_no = port.port_no
                model.onu_device_id = onu.id
                model.name = port.label
                log.debug("[ONU pull step] UNIPort is new, creating it", port_no=port.port_no, onu_device_id=onu.id)

            model.admin_state = AdminState.Types.Name(port.admin_state)
            model.oper_status = OperStatus.Types.Name(port.oper_status)
            model.save_changed_fields()
            update_ports.append(model)
        return update_ports

    def create_or_update_ani_port(self, pon_onu_ports, onu):
        update_ports = []

        for port in pon_onu_ports:
            try:
                model = ANIPort.objects.filter(port_no=port.port_no, onu_device_id=onu.id)[0]
                model.xos_managed = False
                log.debug("[ONU pull step] ANIPort already exists, updating it", port_no=port.port_no, onu_device_id=onu.id)
            except IndexError:
                model = ANIPort()
                model.port_no = port.port_no
                model.onu_device_id = onu.id
                model.name = port.label
                model.xos_managed = False
                log.debug("[ONU pull step] ANIPort is new, creating it", port_no=port.port_no, onu_device_id=onu.id)

            model.admin_state = AdminState.Types.Name(port.admin_state)
            model.oper_status = OperStatus.Types.Name(port.oper_status)
            model.save_changed_fields()
            update_ports.append(model)
        return update_ports
