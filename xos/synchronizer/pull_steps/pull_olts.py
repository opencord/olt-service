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
from xossynchronizer.modelaccessor import OLTDevice, VOLTService, PONPort, NNIPort

from xosconfig import Config
from multistructlog import create_logger

from voltha_protos.common_pb2 import AdminState, OperStatus
from voltha_protos.voltha_pb2 import Port

import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from voltha_client import get_voltha_client
from helpers import Helpers

log = create_logger(Config().get('logging'))


class OLTDevicePullStep(PullStep):
    def __init__(self, model_accessor):
        super(OLTDevicePullStep, self).__init__(model_accessor=model_accessor, observed_model=OLTDevice)

    @staticmethod
    def get_ids_from_logical_device(o):
        # FIXME: this should return a single device from VOLTHA since an instance of Voltha has a single OLT
        try:
            logical_devices = get_voltha_client(o.volt_service).list_logical_devices()
        except Exception as e:
            log.error("[OLT pull step] " + e.message)
            raise e

        for ld in logical_devices:
            if ld.root_device_id == o.device_id:
                o.of_id = ld.id
                o.dp_id = "of:" + Helpers.datapath_id_to_hex(ld.datapath_id)  # convert to hex

        # Note: If the device is administratively disabled, then it's likely we won't find a logical device for
        # it. Only throw the exception for OLTs that are enabled.

        if not o.of_id and not o.dp_id and o.admin_state == "ENABLED":
            raise Exception("Can't find a logical device for device id: %s" % o.device_id)

    def pull_records(self):
        log.debug("[OLT pull step] pulling OLT devices from VOLTHA")
        try:
            self.volt_service = VOLTService.objects.all()[0]
        except IndexError:
            log.warn('VOLTService not found')
            return

        try:
            olt_devices = get_voltha_client(self.volt_service).list_olt_devices()
            if olt_devices is None:
                log.debug("[OLT pull step] Blank response received")
                return
            log.debug("[OLT pull step] received devices", olts=olt_devices)
            olts_in_voltha = self.create_or_update_olts(olt_devices)
            self.delete_olts(olts_in_voltha)
        except Exception as e:
            log.error("[OLT pull step] " + e.message)
            return

    def create_or_update_olts(self, olts):

        updated_olts = []

        for olt in olts:
            olt_ports = self.fetch_olt_ports(olt.id)

            try:
                if olt.type == "simulated_olt":
                    [host, port] = ["172.17.0.1", "50060"]
                if olt.WhichOneof('address') == "host_and_port":
                    [host, port] = olt.host_and_port.split(":")
                    model = OLTDevice.objects.filter(device_type=olt.type, host=host, port=port)[0]

                    log.debug("[OLT pull step] OLTDevice already exists, updating it", device_type=olt.type,
                              id=model.id, host=host, port=port)
                elif olt.mac_address != '':
                    mac_address = olt.mac_address
                    model = OLTDevice.objects.filter(device_type=olt.type, mac_address=mac_address)[0]

                    log.debug("[OLT pull step] OLTDevice already exists, updating it", device_type=olt.type,
                              id=model.id, mac_address=mac_address)
                else:
                    log.error("[OLT pull step] Should never reach this point!")

                if model.enacted < model.updated:
                    log.debug("[OLT pull step] Skipping pull on OLTDevice %s as enacted < updated" % model.name, name=model.name, id=model.id, enacted=model.enacted, updated=model.updated)
                    # if we are not updating the device we still need to pull ports
                    if olt_ports:
                        self.create_or_update_ports(olt_ports, model)
                    updated_olts.append(model)
                    continue

            except IndexError:

                model = OLTDevice()
                model.device_type = olt.type

                if olt.type == "simulated_olt":
                    model.host = "172.17.0.1"
                    model.port = 50060
                    log.debug("[OLT pull step] OLTDevice is new, creating it. Simulated")
                elif olt.WhichOneof('address') == "host_and_port":
                    [host, port] = olt.host_and_port.split(":")
                    model.host = host
                    model.port = int(port)
                    log.debug("[OLT pull step] OLTDevice is new, creating it", device_type=olt.type, host=host, port=port)
                elif olt.mac_address != '':
                    model.mac_address = olt.mac_address
                    log.debug("[OLT pull step] OLTDevice is new, creating it", device_type=olt.type, mac_address=mac_address)

                # there's no name in voltha, so make one up based on the id
                model.name = "OLT-%s" % olt.id

                nni_ports = [p for p in olt_ports if Port.PortType.Name(p.type) == "ETHERNET_NNI"]
                if not nni_ports:
                    log.warning("[OLT pull step] No NNI ports, so no way to determine uplink. Skipping.", device_type=olt.type, host=host, port=port)
                    model.device_id = olt.id  # device_id must be populated for delete_olts
                    updated_olts.append(model)
                    continue

                # Exctract uplink from the first NNI port. This decision is arbitrary, we will worry about multiple
                # NNI ports when that situation arises.
                model.uplink = str(nni_ports[0].port_no)

                # Initial admin_state
                model.admin_state = AdminState.Types.Name(olt.admin_state)

            # Check to see if Voltha's serial_number field is populated. During Activation it's possible that
            # Voltha's serial_number field may be blank. We want to avoid overwriting a populated data model
            # serial number with an unpopulated Voltha serial number. IF this happened, then there would be
            # a window of vulnerability where sadis requests will fail.

            if olt.serial_number != '' and model.serial_number != olt.serial_number:
                # Check to see if data model serial number is already populated. If the serial number was
                # already populated, and what we just learned from Voltha differs, then this is an error
                # that should be made visible to the operator, so the operator may correct it.
                if model.serial_number:
                    log.error("Serial number mismatch when pulling olt. Aborting OLT Update.",
                              model_serial_number=model.serial_number,
                              voltha_serial_number=olt.serial_number,
                              olt_id=model.id)
                    model.backend_status = "Incorrect serial number"
                    model.backend_code = 2
                    model.save_changed_fields()
                    # Have to include this in the result, or delete_olts() will delete it
                    updated_olts.append(model)
                    # Stop processing this OLT
                    continue

                # Preserve existing behavior.
                # Data model serial number is unpopulated, so populate it.

                # TODO(smbaker): Consider making serial_number a required field, then do away with this.
                #                Deferred until after SEBA-2.0 release.

                log.info("Pull step learned olt serial number from voltha",
                         model_serial_number=model.serial_number,
                         voltha_serial_number=olt.serial_number,
                         olt_id=model.id)

                model.serial_number = olt.serial_number

            # Adding feedback state to the device
            model.device_id = olt.id
            model.oper_status = OperStatus.Types.Name(olt.oper_status)

            model.volt_service = self.volt_service
            model.volt_service_id = self.volt_service.id

            # get logical device
            OLTDevicePullStep.get_ids_from_logical_device(model)

            model.save_changed_fields()

            if olt_ports:
                self.create_or_update_ports(olt_ports, model)

            updated_olts.append(model)

        return updated_olts

    def fetch_olt_ports(self, olt_device_id):
        """
        Given an olt device_id, query VOLTHA for the set of ports associated with that OLT.

        :param olt_device_id: The given OLT device id.
        :return: List of port dictionaries, or None in case of error.
        """
        try:
            olt_ports = get_voltha_client(self.volt_service).list_device_ports(olt_device_id)
            if olt_ports is not None:
                log.debug("[OLT pull step] received ports", ports=olt_ports, olt=olt_device_id)
            return olt_ports
        except Exception as e:
            log.error("[OLT pull step] " + e.message)
            return None

    def create_or_update_ports(self, ports, olt):
        nni_ports = [p for p in ports if Port.PortType.Name(p.type) == "ETHERNET_NNI"]
        pon_ports = [p for p in ports if Port.PortType.Name(p.type) == "PON_OLT"]

        self.create_or_update_nni_port(nni_ports, olt)
        self.create_or_update_pon_port(pon_ports, olt)

    def create_or_update_pon_port(self, pon_ports, olt):

        update_ports = []

        for port in pon_ports:
            try:
                model = PONPort.objects.filter(port_no=port.port_no, olt_device_id=olt.id)[0]
                log.debug("[OLT pull step] PONPort already exists, updating it", port_no=port.port_no, olt_device_id=olt.id)
            except IndexError:
                model = PONPort()
                model.port_no = port.port_no
                model.olt_device_id = olt.id
                model.name = port.label
                log.debug("[OLT pull step] PONPort is new, creating it", port_no=port.port_no, olt_device_id=olt.id)

            model.admin_state = AdminState.Types.Name(port.admin_state)
            model.oper_status = OperStatus.Types.Name(port.oper_status)
            model.save_changed_fields()
            update_ports.append(model)
        return update_ports

    def create_or_update_nni_port(self, nni_ports, olt):
        update_ports = []

        for port in nni_ports:
            try:
                model = NNIPort.objects.filter(port_no=port.port_no, olt_device_id=olt.id)[0]
                model.xos_managed = False
                log.debug("[OLT pull step] NNIPort already exists, updating it", port_no=port.port_no, olt_device_id=olt.id)
            except IndexError:
                model = NNIPort()
                model.port_no = port.port_no
                model.olt_device_id = olt.id
                model.name = port.label
                model.xos_managed = False
                log.debug("[OLT pull step] NNIPort is new, creating it", port_no=port.port_no, olt_device_id=olt.id)

            model.admin_state = AdminState.Types.Name(port.admin_state)
            model.oper_status = OperStatus.Types.Name(port.oper_status)
            model.save_changed_fields()
            update_ports.append(model)
        return update_ports

    def delete_olts(self, olts_in_voltha):

        olts_id_in_voltha = [m.device_id for m in olts_in_voltha]

        xos_olts = OLTDevice.objects.all()

        deleted_in_voltha = [o for o in xos_olts if o.device_id not in olts_id_in_voltha]

        for model in deleted_in_voltha:

            if model.enacted < model.updated:
                # DO NOT delete a model that is being processed
                log.debug("[OLT pull step] device is not present in VOLTHA, skipping deletion as sync is in progress", device_id=o.device_id,
                          name=o.name)
                continue

            log.debug("[OLT pull step] deleting device as it's not present in VOLTHA", device_id=o.device_id, name=o.name, id=o.id)
            model.delete()
