
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
from xosapi.convenience.serviceinstance import ORMWrapperServiceInstance

import logging as log

class ORMWrapperVOLTServiceInstance(ORMWrapperServiceInstance):

    def get_olt_device_by_subscriber(self):
        pon_port = self.get_pon_port_by_subscriber()
        return pon_port.olt_device

    def get_pon_port_by_subscriber(self):
        si = self.stub.ServiceInstance.objects.get(id=self.id)
        onu_sn = si.get_westbound_service_instance_properties("onu_device")
        onu = self.stub.ONUDevice.objects.get(serial_number=onu_sn)
        return onu.pon_port

    @property
    def switch_datapath_id(self):
        try:
            olt_device = self.get_olt_device_by_subscriber()
            if olt_device:
                return olt_device.switch_datapath_id
            return None
        except Exception, e:
            log.exception('Error while reading switch_datapath_id: %s' % e.message)
            return None

    @property
    def switch_port(self):
        try:
            olt_device = self.get_olt_device_by_subscriber()
            if olt_device:
                return olt_device.switch_port
            return None
        except Exception, e:
            log.exception('Error while reading switch_port: %s' % e.message)
            return None

    @property
    def outer_tpid(self):
        try:
            olt_device = self.get_olt_device_by_subscriber()
            if olt_device:
                return olt_device.outer_tpid
            return None
        except Exception, e:
            log.exception('Error while reading outer_tpid: %s' % e.message)
            return None


register_convenience_wrapper("VOLTServiceInstance", ORMWrapperVOLTServiceInstance)
