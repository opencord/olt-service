
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


def __init__(self, *args, **kwargs):
    volt_services = VOLTService.objects.all()
    if volt_services:
        self._meta.get_field("owner").default = volt_services[0].id
    super(VOLTTenant, self).__init__(*args, **kwargs)
    self.cached_vcpe = None

def __xos_save_base(self, *args, **kwargs):
    if not self.creator:
        if not getattr(self, "caller", None):
            # caller must be set when creating a vCPE since it creates a slice
            raise XOSProgrammingError("VOLTTenant's self.caller was not set")
        self.creator = self.caller
        if not self.creator:
            raise XOSProgrammingError("VOLTTenant's self.creator was not set")

    return False
