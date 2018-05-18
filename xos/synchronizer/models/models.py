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

from core.models.xosbase import *

from models_decl import VOLTService_decl
from models_decl import VOLTServiceInstance_decl
from models_decl import OLTDevice_decl
from models_decl import PONPort_decl
from models_decl import ONUDevice_decl

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


class PONPort(PONPort_decl):
    class Meta:
        proxy = True 


class ONUDevice(ONUDevice_decl):
    class Meta:
        proxy = True 

