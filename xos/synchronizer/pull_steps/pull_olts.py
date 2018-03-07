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

from synchronizers.new_base.pullstep import PullStep
from synchronizers.new_base.modelaccessor import OLTDevice

from xosconfig import Config
from multistructlog import create_logger

log = create_logger(Config().get('logging'))

class OLTDevicePullStep(PullStep):
    def __init__(self):
        super(OLTDevicePullStep, self).__init__(observed_model=OLTDevice)

    def pull_records(self):
        log.info("pulling OLT devices from VOLTHA")
