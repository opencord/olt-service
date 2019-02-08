#!/usr/bin/python

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

from __future__ import unicode_literals

import core.models.xosbase_header
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0002_initial_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='OLTDevice_decl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, help_text=b'Time this model was created')),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer')),
                ('enacted', models.DateTimeField(blank=True, default=None, help_text=b'When synced, set to the timestamp of the data that was synced', null=True)),
                ('policed', models.DateTimeField(blank=True, default=None, help_text=b'When policed, set to the timestamp of the data that was policed', null=True)),
                ('backend_register', models.CharField(blank=True, default=b'{}', max_length=1024, null=True)),
                ('backend_need_delete', models.BooleanField(default=False)),
                ('backend_need_reap', models.BooleanField(default=False)),
                ('backend_status', models.CharField(default=b'Provisioning in progress', max_length=1024, null=True)),
                ('backend_code', models.IntegerField(default=0)),
                ('deleted', models.BooleanField(default=False)),
                ('write_protect', models.BooleanField(default=False)),
                ('lazy_blocked', models.BooleanField(default=False)),
                ('no_sync', models.BooleanField(default=False)),
                ('no_policy', models.BooleanField(default=False)),
                ('policy_status', models.CharField(blank=True, default=b'Policy in process', max_length=1024, null=True)),
                ('policy_code', models.IntegerField(blank=True, default=0, null=True)),
                ('leaf_model_name', models.CharField(help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024)),
                ('backend_need_delete_policy', models.BooleanField(default=False, help_text=b'True if delete model_policy must be run before object can be reaped')),
                ('xos_managed', models.BooleanField(default=True, help_text=b'True if xos is responsible for creating/deleting this object')),
                ('backend_handle', models.CharField(blank=True, help_text=b'Handle used by the backend to track this object', max_length=1024, null=True)),
                ('changed_by_step', models.DateTimeField(blank=True, default=None, help_text=b'Time this model was changed by a sync step', null=True)),
                ('changed_by_policy', models.DateTimeField(blank=True, default=None, help_text=b'Time this model was changed by a model policy', null=True)),
                ('name', models.CharField(blank=True, help_text=b'Human-readable name of device', max_length=254, null=True, unique=True)),
                ('device_type', models.CharField(default=b'openolt', help_text=b'Phyiscal Device Type', max_length=254)),
                ('host', models.CharField(blank=True, help_text=b'IP Address of physical OLT Device', max_length=254, null=True)),
                ('port', models.IntegerField(blank=True, help_text=b'Port Number of physical OLT Device', null=True)),
                ('mac_address', models.TextField(blank=True, help_text=b'Mac address of physical OLT Device', null=True)),
                ('serial_number', models.TextField(blank=True, help_text=b'Serial Number', null=True)),
                ('device_id', models.TextField(blank=True, help_text=b'Voltha Device ID', null=True)),
                ('admin_state', models.TextField(blank=True, choices=[(b'DISABLED', b'DISABLED'), (b'ENABLED', b'ENABLED')], default=b'ENABLED', help_text=b'admin state, whether OLT should be enabled', null=True)),
                ('oper_status', models.TextField(blank=True, help_text=b'operational status, whether OLT is active', null=True)),
                ('of_id', models.TextField(blank=True, help_text=b'Logical device openflow id', null=True)),
                ('dp_id', models.TextField(blank=True, help_text=b'Logical device datapath id', null=True)),
                ('uplink', models.TextField(help_text=b'uplink port, exposed via sadis')),
                ('driver', models.TextField(default=b'voltha', help_text=b'DEPRECATED')),
                ('switch_datapath_id', models.TextField(blank=True, help_text=b'Fabric switch to which the OLT is connected', null=True)),
                ('switch_port', models.TextField(blank=True, help_text=b'Fabric port to which the OLT is connected', null=True)),
                ('outer_tpid', models.TextField(blank=True, help_text=b'Outer VLAN id field EtherType', null=True)),
                ('nas_id', models.TextField(blank=True, help_text=b'Authentication ID (propagated to the free-radius server via sadis)', null=True)),
            ],
            options={
                'verbose_name': 'OLT Device',
            },
            bases=(models.Model, core.models.xosbase_header.PlModelMixIn),
        ),
        migrations.CreateModel(
            name='ONUDevice_decl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, help_text=b'Time this model was created')),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer')),
                ('enacted', models.DateTimeField(blank=True, default=None, help_text=b'When synced, set to the timestamp of the data that was synced', null=True)),
                ('policed', models.DateTimeField(blank=True, default=None, help_text=b'When policed, set to the timestamp of the data that was policed', null=True)),
                ('backend_register', models.CharField(blank=True, default=b'{}', max_length=1024, null=True)),
                ('backend_need_delete', models.BooleanField(default=False)),
                ('backend_need_reap', models.BooleanField(default=False)),
                ('backend_status', models.CharField(default=b'Provisioning in progress', max_length=1024, null=True)),
                ('backend_code', models.IntegerField(default=0)),
                ('deleted', models.BooleanField(default=False)),
                ('write_protect', models.BooleanField(default=False)),
                ('lazy_blocked', models.BooleanField(default=False)),
                ('no_sync', models.BooleanField(default=False)),
                ('no_policy', models.BooleanField(default=False)),
                ('policy_status', models.CharField(blank=True, default=b'Policy in process', max_length=1024, null=True)),
                ('policy_code', models.IntegerField(blank=True, default=0, null=True)),
                ('leaf_model_name', models.CharField(help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024)),
                ('backend_need_delete_policy', models.BooleanField(default=False, help_text=b'True if delete model_policy must be run before object can be reaped')),
                ('xos_managed', models.BooleanField(default=True, help_text=b'True if xos is responsible for creating/deleting this object')),
                ('backend_handle', models.CharField(blank=True, help_text=b'Handle used by the backend to track this object', max_length=1024, null=True)),
                ('changed_by_step', models.DateTimeField(blank=True, default=None, help_text=b'Time this model was changed by a sync step', null=True)),
                ('changed_by_policy', models.DateTimeField(blank=True, default=None, help_text=b'Time this model was changed by a model policy', null=True)),
                ('serial_number', models.CharField(help_text=b'Serial number of ONU Device', max_length=254, unique=True)),
                ('vendor', models.CharField(help_text=b'Vendor of ONU Device', max_length=254)),
                ('device_type', models.CharField(default=b'asfvolt16_olt', help_text=b'Device Type', max_length=254)),
                ('device_id', models.CharField(blank=True, help_text=b'Voltha Device ID', max_length=254, null=True)),
                ('admin_state', models.TextField(blank=True, choices=[(b'DISABLED', b'DISABLED'), (b'ENABLED', b'ENABLED')], default=b'ENABLED', help_text=b'admin state, whether port should be enabled', null=True)),
                ('oper_status', models.TextField(blank=True, help_text=b'oper_status', null=True)),
                ('connect_status', models.TextField(blank=True, help_text=b'operational status, whether port is active', null=True)),
                ('reason', models.TextField(blank=True, help_text=b'ONU device configuration state machine status message', null=True)),
            ],
            options={
                'verbose_name': 'ONU Device',
            },
            bases=(models.Model, core.models.xosbase_header.PlModelMixIn),
        ),
        migrations.CreateModel(
            name='PortBase_decl',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, help_text=b'Time this model was created')),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer')),
                ('enacted', models.DateTimeField(blank=True, default=None, help_text=b'When synced, set to the timestamp of the data that was synced', null=True)),
                ('policed', models.DateTimeField(blank=True, default=None, help_text=b'When policed, set to the timestamp of the data that was policed', null=True)),
                ('backend_register', models.CharField(blank=True, default=b'{}', max_length=1024, null=True)),
                ('backend_need_delete', models.BooleanField(default=False)),
                ('backend_need_reap', models.BooleanField(default=False)),
                ('backend_status', models.CharField(default=b'Provisioning in progress', max_length=1024, null=True)),
                ('backend_code', models.IntegerField(default=0)),
                ('deleted', models.BooleanField(default=False)),
                ('write_protect', models.BooleanField(default=False)),
                ('lazy_blocked', models.BooleanField(default=False)),
                ('no_sync', models.BooleanField(default=False)),
                ('no_policy', models.BooleanField(default=False)),
                ('policy_status', models.CharField(blank=True, default=b'Policy in process', max_length=1024, null=True)),
                ('policy_code', models.IntegerField(blank=True, default=0, null=True)),
                ('leaf_model_name', models.CharField(help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024)),
                ('backend_need_delete_policy', models.BooleanField(default=False, help_text=b'True if delete model_policy must be run before object can be reaped')),
                ('xos_managed', models.BooleanField(default=True, help_text=b'True if xos is responsible for creating/deleting this object')),
                ('backend_handle', models.CharField(blank=True, help_text=b'Handle used by the backend to track this object', max_length=1024, null=True)),
                ('changed_by_step', models.DateTimeField(blank=True, default=None, help_text=b'Time this model was changed by a sync step', null=True)),
                ('changed_by_policy', models.DateTimeField(blank=True, default=None, help_text=b'Time this model was changed by a model policy', null=True)),
                ('name', models.TextField(db_index=True, help_text=b'Human-readable name of port')),
                ('port_no', models.IntegerField(help_text=b'Port Number')),
                ('admin_state', models.TextField(blank=True, help_text=b'admin state, whether port should be enabled', null=True)),
                ('oper_status', models.TextField(blank=True, help_text=b'operational status, whether port is active', null=True)),
            ],
            options={
                'verbose_name': 'PortBase',
            },
            bases=(models.Model, core.models.xosbase_header.PlModelMixIn),
        ),
        migrations.CreateModel(
            name='VOLTService_decl',
            fields=[
                ('service_decl_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.Service_decl')),
                ('voltha_url', models.CharField(default=b'voltha.voltha.svc.cluster.local', help_text=b'The Voltha API address. By default voltha.voltha.svc.cluster.local', max_length=254)),
                ('voltha_port', models.IntegerField(default=8882, help_text=b'The Voltha API port. By default 8882')),
                ('voltha_user', models.CharField(default=b'voltha', help_text=b'The Voltha username. By default voltha', max_length=254)),
                ('voltha_pass', models.CharField(default=b'admin', help_text=b'The Voltha password. By default admin', max_length=254)),
                ('onos_voltha_url', models.CharField(default=b'onos-voltha-ui.voltha.svc.cluster.local', help_text=b'The ONOS Voltha address. By default onos-voltha-ui.voltha.svc.cluster.local', max_length=254)),
                ('onos_voltha_port', models.IntegerField(default=8181, help_text=b'The Voltha API port. By default 8181')),
                ('onos_voltha_user', models.CharField(default=b'onos', help_text=b'The ONOS Voltha username. By default sdn', max_length=254)),
                ('onos_voltha_pass', models.CharField(default=b'rocks', help_text=b'The ONOS Voltha password. By default rocks', max_length=254)),
            ],
            options={
                'verbose_name': 'vOLT Service',
            },
            bases=('core.service',),
        ),
        migrations.CreateModel(
            name='VOLTServiceInstance_decl',
            fields=[
                ('serviceinstance_decl_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.ServiceInstance_decl')),
                ('description', models.CharField(blank=True, help_text=b'Human-readable description', max_length=254, null=True)),
                ('onu_device', models.ForeignKey(blank=True, help_text=b'ONUDevice that belongs to this Subscriber chain', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='volt_service_instances', to='volt.ONUDevice_decl')),
            ],
            options={
                'verbose_name': 'vOLT Service Instance',
            },
            bases=('core.serviceinstance',),
        ),
        migrations.CreateModel(
            name='NNIPort_decl',
            fields=[
                ('portbase_decl_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='volt.PortBase_decl')),
            ],
            options={
                'verbose_name': 'NNI Port',
            },
            bases=('volt.portbase_decl',),
        ),
        migrations.CreateModel(
            name='PONONUPort_decl',
            fields=[
                ('portbase_decl_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='volt.PortBase_decl')),
            ],
            options={
                'verbose_name': 'ANI Port',
            },
            bases=('volt.portbase_decl',),
        ),
        migrations.CreateModel(
            name='PONPort_decl',
            fields=[
                ('portbase_decl_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='volt.PortBase_decl')),
            ],
            options={
                'verbose_name': 'PON Port',
            },
            bases=('volt.portbase_decl',),
        ),
        migrations.CreateModel(
            name='UNIPort_decl',
            fields=[
                ('portbase_decl_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='volt.PortBase_decl')),
            ],
            options={
                'verbose_name': 'UNI Port',
            },
            bases=('volt.portbase_decl',),
        ),
        migrations.AddField(
            model_name='oltdevice_decl',
            name='volt_service',
            field=models.ForeignKey(help_text=b'VOLTService that owns this OLT', on_delete=django.db.models.deletion.CASCADE, related_name='volt_devices', to='volt.VOLTService_decl'),
        ),
        migrations.CreateModel(
            name='OLTDevice',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.oltdevice_decl',),
        ),
        migrations.CreateModel(
            name='ONUDevice',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.onudevice_decl',),
        ),
        migrations.CreateModel(
            name='PortBase',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.portbase_decl',),
        ),
        migrations.CreateModel(
            name='VOLTService',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.voltservice_decl',),
        ),
        migrations.CreateModel(
            name='VOLTServiceInstance',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.voltserviceinstance_decl',),
        ),
        migrations.AddField(
            model_name='uniport_decl',
            name='onu_device',
            field=models.ForeignKey(help_text=b'ONUDevice that owns this UNIPort', on_delete=django.db.models.deletion.CASCADE, related_name='uni_ports', to='volt.ONUDevice_decl'),
        ),
        migrations.AddField(
            model_name='ponport_decl',
            name='olt_device',
            field=models.ForeignKey(help_text=b'OLTDevice that owns this PONPort', on_delete=django.db.models.deletion.CASCADE, related_name='pon_ports', to='volt.OLTDevice_decl'),
        ),
        migrations.AddField(
            model_name='pononuport_decl',
            name='onu_device',
            field=models.ForeignKey(help_text=b'ONUDevice that owns this PONONUPort', on_delete=django.db.models.deletion.CASCADE, related_name='pononu_ports', to='volt.ONUDevice_decl'),
        ),
        migrations.AddField(
            model_name='onudevice_decl',
            name='pon_port',
            field=models.ForeignKey(help_text=b'PONPort that connects this ONUDevice to an OLTDevice', on_delete=django.db.models.deletion.CASCADE, related_name='onu_devices', to='volt.PONPort_decl'),
        ),
        migrations.AlterUniqueTogether(
            name='oltdevice_decl',
            unique_together=set([('host', 'port')]),
        ),
        migrations.AddField(
            model_name='nniport_decl',
            name='olt_device',
            field=models.ForeignKey(help_text=b'OLTDevice that owns this NNIPort', on_delete=django.db.models.deletion.CASCADE, related_name='nni_ports', to='volt.OLTDevice_decl'),
        ),
        migrations.CreateModel(
            name='NNIPort',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.nniport_decl',),
        ),
        migrations.CreateModel(
            name='PONONUPort',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.pononuport_decl',),
        ),
        migrations.CreateModel(
            name='PONPort',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.ponport_decl',),
        ),
        migrations.CreateModel(
            name='UNIPort',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('volt.uniport_decl',),
        ),
    ]
