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

import random

from xos.exceptions import XOSValidationError

from models_decl import VOLTService_decl
from models_decl import VOLTServiceInstance_decl
from models_decl import OLTDevice_decl
from models_decl import PONPort_decl
from models_decl import NNIPort_decl
from models_decl import ONUDevice_decl
from models_decl import PONONUPort_decl
from models_decl import UNIPort_decl

class VOLTService(VOLTService_decl):
    class Meta:
        proxy = True

    @staticmethod
    def has_access_device(serial_number):
        try:
            ONUDevice.objects.get(serial_number=serial_number)
            return True
        except IndexError, e:
            return False

class VOLTServiceInstance(VOLTServiceInstance_decl):
    class Meta:
        proxy = True

class OLTDevice(OLTDevice_decl):
    class Meta:
        proxy = True

    def get_volt_si(self):
        return VOLTServiceInstance.objects.all()

    def save(self, *args, **kwargs):

        if (self.host or self.port) and self.mac_address:
            raise XOSValidationError("You can't specify both host/port and mac_address for OLTDevice [host=%s, port=%s, mac_address=%s]" % (self.host, self.port, self.mac_address))

        super(OLTDevice, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):

        onus = []
        pon_ports = self.pon_ports.all()
        for port in pon_ports:
            onus = onus + list(port.onu_devices.all())


        if len(onus) > 0:
            onus = [o.id for o in onus]

            # find the ONUs used by VOLTServiceInstances
            used_onus = [o.onu_device_id for o in self.get_volt_si()]

            # find the intersection between the onus associated with this OLT and the used one
            used_onus_to_delete = [o for o in onus if o in used_onus]

            if len(used_onus_to_delete) > 0:
                if hasattr(self, "device_id") and self.device_id:
                    item = self.device_id
                elif hasattr(self, "name") and self.name:
                    item = self.name
                else:
                    item = self.id
                raise XOSValidationError('OLT "%s" can\'t be deleted as it has subscribers associated with its ONUs' % item)

        super(OLTDevice, self).delete(*args, **kwargs)

class PONPort(PONPort_decl):
    class Meta:
        proxy = True

    def generate_tag(self):
        # NOTE this method will loop if available c_tags are ended
        tag = random.randint(16, 4096)
        if tag in self.get_used_s_tags():
            return self.generate_tag()
        return tag

    def get_used_s_tags(self):
        same_olt_device = OLTDevice.objects.filter(device_id=self.olt_device)
        return [s.c_tag for s in same_olt_device]

    def save(self, *args, **kwargs):
        # validate s_tag
        if hasattr(self, 's_tag') and self.s_tag is not None:
            is_update_with_same_tag = False

            if not self.is_new:
                # if it is an update, but the tag is the same, skip validation
                existing = PONPort.objects.filter(s_tag=self.s_tag)

                if len(existing) > 0 and existing[0].s_tag == self.s_tag and existing[0].id == self.id:
                    is_update_with_same_tag = True

            if self.s_tag in self.get_used_s_tags() and not is_update_with_same_tag:
                raise XOSValidationError(
                    "The s_tag you specified (%s) has already been used on device %s" % (self.s_tag, self.onu_device))

        if not hasattr(self, "s_tag") or self.s_tag is None:
            self.s_tag = self.generate_tag()

        super(PONPort, self).save(*args, **kwargs)


class NNIPort(NNIPort_decl):
    class Meta:
        proxy = True


class ONUDevice(ONUDevice_decl):
    class Meta:
        proxy = True

class PONONUPort(PONONUPort_decl):
    class Meta:
        proxy = True

class UNIPort(UNIPort_decl):
    class Meta:
        proxy = True

