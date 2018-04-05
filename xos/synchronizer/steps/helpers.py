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

class Helpers():
    @staticmethod
    def format_url(url):
        if 'http' in url:
            return url
        else:
            return 'http://%s' % url

    @staticmethod
    def get_voltha_info(olt_service):
        return {
            'url': Helpers.format_url(olt_service.voltha_url),
            'user': olt_service.voltha_user,
            'pass': olt_service.voltha_pass
        }

    @staticmethod
    def get_p_onos_info(olt_service):
        return {
            'url': Helpers.format_url(olt_service.p_onos_url),
            'user': olt_service.p_onos_user,
            'pass': olt_service.p_onos_pass
        }

    @staticmethod
    def datapath_id_to_hex(id):
        if isinstance(id, basestring):
            id = int(id)
        return "{0:0{1}x}".format(id, 16)