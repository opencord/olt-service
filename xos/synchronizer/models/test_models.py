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

import unittest
from mock import patch, Mock, MagicMock

# mocking XOS exception, as they're based in Django
class Exceptions:
    XOSValidationError = Exception
    XOSNotFound = Exception

class XOS:
    exceptions = Exceptions

class TestOLTDeviceModel(unittest.TestCase):
    def setUp(self):
        self.xos = XOS

        self.models_decl = Mock()
        self.models_decl.OLTDevice_decl = MagicMock
        self.models_decl.OLTDevice_decl.delete = Mock()

        modules = {
            'xos': MagicMock(),
            'xos.exceptions': self.xos.exceptions,
            'models_decl': self.models_decl,
        }

        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()

        from models import OLTDevice

        self.olt_device = OLTDevice()
        self.olt_device.id = None # this is a new model
        self.olt_device.is_new = True
        self.olt_device.device_id = 1234

    def tearDown(self):
        self.module_patcher.stop()

    def test_create_mac_address(self):
        from models import OLTDevice
        olt = OLTDevice()

        olt.host = "1.1.1.1"
        olt.port = "9101"
        olt.mac_address = "00:0c:d5:00:05:40"

        with self.assertRaises(Exception) as e:
            olt.save()

        self.assertEqual(e.exception.message,
                         "You can't specify both host/port and mac_address for OLTDevice [host=%s, port=%s, mac_address=%s]" % (olt.host, olt.port, olt.mac_address))

    def test_delete(self):
        self.olt_device.delete()
        self.models_decl.OLTDevice_decl.delete.assert_called()

    def test_prevent_delete(self):

        onu1 = Mock()
        onu1.id = 1

        pon1 = Mock()
        pon1.onu_devices.all.return_value = [onu1]

        self.olt_device.pon_ports.all.return_value = [pon1]

        volt_si_1 = Mock()
        volt_si_1.onu_device_id = onu1.id

        with patch.object(self.olt_device, "get_volt_si")as volt_si_get:
            volt_si_get.return_value = [volt_si_1]
            with self.assertRaises(Exception) as e:
                self.olt_device.delete()

            self.assertEqual(e.exception.message, 'OLT "1234" can\'t be deleted as it has subscribers associated with its ONUs')
            self.models_decl.OLTDevice_decl.delete.assert_not_called()

class TestONUDeviceModel(unittest.TestCase):

    def setUp(self):
        self.xos = XOS

        self.models_decl = Mock()
        self.models_decl.ONUDevice_decl = MagicMock
        self.models_decl.ONUDevice_decl.delete = Mock()

        modules = {
            'xos': MagicMock(),
            'xos.exceptions': self.xos.exceptions,
            'models_decl': self.models_decl,
        }

        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()

        from models import ONUDevice

        self.onu_device = ONUDevice()
        self.onu_device.id = None  # this is a new model
        self.onu_device.is_new = True
        self.onu_device.serial_number = 1234

    def tearDown(self):
        self.module_patcher.stop()

    def test_delete(self):
        self.onu_device.delete()
        self.models_decl.ONUDevice_decl.delete.assert_called()

    def test_prevent_delete(self):
        volt_si_1 = Mock()
        volt_si_1.onu_device_id = self.onu_device.id
        self.onu_device.volt_service_instances.all.return_value = [volt_si_1]

        with self.assertRaises(Exception) as e:
            self.onu_device.delete()

        self.assertEqual(e.exception.message,
                         'ONU "1234" can\'t be deleted as it has subscribers associated with it')
        self.models_decl.OLTDevice_decl.delete.assert_not_called()


class TestTechnologyProfileModel(unittest.TestCase):

    def setUp(self):
        self.xos = XOS

        self.models_decl = Mock()
        self.models_decl.TechnologyProfile_decl = MagicMock
        self.models_decl.TechnologyProfile_decl.save = Mock()
        self.models_decl.TechnologyProfile_decl.objects = Mock()
        self.models_decl.TechnologyProfile_decl.objects.filter.return_value = []

        modules = {
            'xos': MagicMock(),
            'xos.exceptions': self.xos.exceptions,
            'models_decl': self.models_decl
        }

        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()

        from models import TechnologyProfile

        self.technology_profile = TechnologyProfile()
        self.technology_profile.deleted = False
        self.technology_profile.id = None  # this is a new model
        self.technology_profile.is_new = True
        self.technology_profile.technology = 'xgspon'
        self.technology_profile.profile_id = 64
        self.technology_profile.profile_value = '{ "name": "4QueueHybridProfileMap1", "profile_type": "XPON", "version": 1, "num_gem_ports": 4, "instance_control": { "onu": "multi-instance", "uni": "single-instance", "max_gem_payload_size": "auto" }, "us_scheduler": { "additional_bw": "auto", "direction": "UPSTREAM", "priority": 0, "weight": 0, "q_sched_policy": "hybrid" }, "ds_scheduler": { "additional_bw": "auto", "direction": "DOWNSTREAM", "priority": 0, "weight": 0, "q_sched_policy": "hybrid" }, "upstream_gem_port_attribute_list": [ { "pbit_map": "0b00000101", "aes_encryption": "True", "scheduling_policy": "WRR", "priority_q": 4, "weight": 25, "discard_policy": "TailDrop", "max_q_size": "auto", "discard_config": { "max_threshold": 0, "min_threshold": 0, "max_probability": 0 } }, { "pbit_map": "0b00011010", "aes_encryption": "True", "scheduling_policy": "WRR", "priority_q": 3, "weight": 75, "discard_policy": "TailDrop", "max_q_size": "auto", "discard_config": { "min_threshold": 0, "max_threshold": 0, "max_probability": 0 } }, { "pbit_map": "0b00100000", "aes_encryption": "True", "scheduling_policy": "StrictPriority", "priority_q": 2, "weight": 0, "discard_policy": "TailDrop", "max_q_size": "auto", "discard_config": { "min_threshold": 0, "max_threshold": 0, "max_probability": 0 } }, { "pbit_map": "0b11000000", "aes_encryption": "True", "scheduling_policy": "StrictPriority", "priority_q": 1, "weight": 25, "discard_policy": "TailDrop", "max_q_size": "auto", "discard_config": { "min_threshold": 0, "max_threshold": 0, "max_probability": 0 } } ], "downstream_gem_port_attribute_list": [ { "pbit_map": "0b00000101", "aes_encryption": "True", "scheduling_policy": "WRR", "priority_q": 4, "weight": 10, "discard_policy": "TailDrop", "max_q_size": "auto", "discard_config": { "min_threshold": 0, "max_threshold": 0, "max_probability": 0 } }, { "pbit_map": "0b00011010", "aes_encryption": "True", "scheduling_policy": "WRR", "priority_q": 3, "weight": 90, "discard_policy": "TailDrop", "max_q_size": "auto", "discard_config": { "min_threshold": 0, "max_threshold": 0, "max_probability": 0 } }, { "pbit_map": "0b00100000", "aes_encryption": "True", "scheduling_policy": "StrictPriority", "priority_q": 2, "weight": 0, "discard_policy": "TailDrop", "max_q_size": "auto", "discard_config": { "min_threshold": 0, "max_threshold": 0, "max_probability": 0 } }, { "pbit_map": "0b11000000", "aes_encryption": "True", "scheduling_policy": "StrictPriority", "priority_q": 1, "weight": 25, "discard_policy": "TailDrop", "max_q_size": "auto", "discard_config": { "min_threshold": 0, "max_threshold": 0, "max_probability": 0 } } ]}'

    def tearDown(self):
        self.module_patcher.stop()

    def test_save(self):
        self.technology_profile.save()
        self.models_decl.TechnologyProfile_decl.save.assert_called()

    def test_allow_save_if_nohing_changed(self):
        self.technology_profile.is_new = False
        self.technology_profile.id = 1
        self.technology_profile.profile_value = '{"name": "someValue", "profile_type": "someValue"}'
        self.technology_profile.diff.keys.return_value = []

        self.technology_profile.save()
        self.models_decl.TechnologyProfile_decl.save.assert_called()

    def test_prevent_modify(self):
        self.technology_profile.is_new = False
        self.technology_profile.id = 1
        self.technology_profile.profile_value = '{"name": "someValue", "profile_type": "someValue"}'
        self.technology_profile.diff.keys.return_value = ["some"]

        self.models_decl.TechnologyProfile_decl.objects.filter.return_value = [self.technology_profile]

        with self.assertRaises(Exception) as e:
            self.technology_profile.save()

        self.assertEqual(e.exception.message,
                         'Modification operation is not allowed on Technology Profile [/xgspon/64]. Delete it and add again')
        self.models_decl.TechnologyProfile_decl.save.assert_not_called()

    def test_invalid_tech_profile_value_format(self):
        self.technology_profile.profile_value = 'someTechProfileValue'

        with self.assertRaises(Exception) as e:
            self.technology_profile.save()

        self.assertEqual(e.exception.message,
                         'Technology Profile value not in valid JSON format')
        self.models_decl.TechnologyProfile_decl.save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
