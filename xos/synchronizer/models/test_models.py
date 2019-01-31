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

if __name__ == '__main__':
    unittest.main()
