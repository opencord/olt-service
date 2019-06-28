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

from xos.exceptions import XOSValidationError, XOSNotFound

from models_decl import VOLTService_decl
from models_decl import VOLTServiceInstance_decl, VOLTServiceInstance
from models_decl import OLTDevice_decl
from models_decl import PortBase_decl, PortBase
from models_decl import PONPort_decl, PONPort
from models_decl import NNIPort_decl, NNIPort
from models_decl import ONUDevice_decl
from models_decl import ANIPort_decl, ANIPort
from models_decl import UNIPort_decl, UNIPort
from models_decl import TechnologyProfile_decl
from django.core.exceptions import ObjectDoesNotExist

import json


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

    def get_olt_technology_from_unu_sn(self, onu_sn):
        """
        Return the technology assigned to an OLT Device given and ONU Serial Number
        example usage:
            volt = VOLTService.objects.first()
            sn = volt.get_olt_technology_from_unu_sn("BRCM12345678")
            # "XGSPON"

        Arguments:
            onu_sn {string} -- The ONU Serial Number

        Returns:
            string -- Technology
        """
        try:
            onu = ONUDevice.objects.get(serial_number=onu_sn)
            olt = onu.pon_port.olt_device
            return olt.technology
        except ObjectDoesNotExist:
            raise XOSNotFound("Can't find OLT for %s" % onu_sn)

    def get_tech_profile(self, technology, profile_id):
        """
        Returns a Technology profiles or raise an Exception (DoesNotExist)
        :param technology: string
        :param profile_id: int
        :return: TechnologyProfile
        """
        return TechnologyProfile.objects.get(technology=technology, profile_id=profile_id)


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


class ONUDevice(ONUDevice_decl):
    class Meta:
        proxy = True

    def delete(self, *args, **kwargs):

        if len(self.volt_service_instances.all()) > 0:
            raise XOSValidationError('ONU "%s" can\'t be deleted as it has subscribers associated with it' % self.serial_number)

        super(ONUDevice, self).delete(*args, **kwargs)


class TechnologyProfile(TechnologyProfile_decl):
    class Meta:
        proxy = True

    def save(self, *args, **kwargs):

        caller_kind = None
        if "caller_kind" in kwargs:
            caller_kind = kwargs.get("caller_kind")

        # only synchronizer is allowed to update the model
        if not self.is_new and caller_kind != "synchronizer":
            if not self.deleted and len(self.diff.keys()) > 0:
                existing = TechnologyProfile.objects.filter(id=self.id)
                raise XOSValidationError('Modification operation is not allowed on Technology Profile [/%s/%s]. Delete it and add again' % (existing[0].technology, existing[0].profile_id))

        # validate if technology profile value is valid JSON format string
        if self.profile_value != None:
            try:
                tp_json_val = json.loads(self.profile_value)
            except ValueError as e:
                raise XOSValidationError('Technology Profile value not in valid JSON format')

        # TODO validate the tech profile (in the model), see errors like:
        # num_gem_ports=tech_profile[TechProfile.NUM_GEM_PORTS],\nKeyError: \'num_gem_ports\''
        # in File "/voltha/common/tech_profile/tech_profile.py", line 403, in _get_tech_profile

        super(TechnologyProfile, self).save(*args, **kwargs)

