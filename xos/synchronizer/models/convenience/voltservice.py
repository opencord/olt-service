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

from xosapi.orm import ORMWrapper, register_convenience_wrapper
from xosapi.convenience.service import ORMWrapperService

import logging as log


class ORMWrapperVOLTService(ORMWrapperService):

    def get_onu_sn_from_openflow(self, dp_id, port_no):
        """Return the ONU serial number from logical_device informations

        example usage:
            volt = VOLTService.objects.first()
            sn = volt.get_onu_from_openflow("of:0000000ce2314000", 2)
            # BRCM1234

        Arguments:
            dp_id {string} -- The openflow id of the OLT device
            port_no {int} -- The openflow port id (UNI Port)

        Returns:
            string -- ONU Serial Number
        """

        log.debug("Searching ONUDevice for %s:%s" % (dp_id, port_no))
        try:
            olt = self.stub.OLTDevice.objects.get(dp_id=dp_id)
            uni_ports = self.stub.UNIPort.objects.filter(port_no=port_no)
            onu = [o.onu_device for o in uni_ports if o.onu_device.pon_port.olt_device.id == olt.id][0]
            return onu.serial_number
        except IndexError:
            log.error("Can't find ONU for %s:%s" % (dp_id, port_no))
        except Exception:
            log.exception("Error while finding ONUDevice for %s:%s" % (dp_id, port_no))


register_convenience_wrapper("VOLTService", ORMWrapperVOLTService)
