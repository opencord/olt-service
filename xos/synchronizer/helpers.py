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
            'url': olt_service.voltha_url,
            'port': olt_service.voltha_port,
        }

    @staticmethod
    def get_onos(olt_service):
        # get the onos service
        onos = [s.leaf_model for s in olt_service.provider_services if "onos" in s.name.lower()]

        if len(onos) == 0:
            raise Exception('Cannot find ONOS service in provider_services of vOLTService')

        return onos[0]

    @staticmethod
    def get_onos_service_name(olt_service):
        onos = Helpers.get_onos(olt_service)

        return onos.name

    @staticmethod
    def get_onos_voltha_info(olt_service):

        onos = Helpers.get_onos(olt_service)

        return {
            'url': Helpers.format_url(onos.rest_hostname),
            'port': onos.rest_port,
            'user': onos.rest_username,
            'pass': onos.rest_password
        }

    @staticmethod
    def datapath_id_to_hex(id):
        if isinstance(id, basestring):
            id = int(id)
        return "{0:0{1}x}".format(id, 16)
