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

# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-04-10 04:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('volt', '0004_oltdevice_decl_link_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='admin_state',
            field=models.CharField(blank=True, choices=[(b'DISABLED', b'DISABLED'), (b'ENABLED', b'ENABLED')], default=b'ENABLED', help_text=b'admin state, whether OLT should be enabled', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='device_id',
            field=models.CharField(blank=True, help_text=b'Voltha Device ID', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='device_type',
            field=models.CharField(default=b'openolt', help_text=b'Phyiscal Device Type', max_length=256),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='dp_id',
            field=models.CharField(blank=True, help_text=b'Logical device datapath id', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='driver',
            field=models.CharField(default=b'voltha', help_text=b'DEPRECATED', max_length=32),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='host',
            field=models.CharField(blank=True, help_text=b'IP Address of physical OLT Device', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='link_status',
            field=models.CharField(blank=True, choices=[(b'up', b'up'), (b'down', b'down')], help_text=b'connectivity status, whether OLT has connectivity to agg switch', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='mac_address',
            field=models.CharField(blank=True, help_text=b'MAC address of physical OLT Device', max_length=17, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='name',
            field=models.CharField(blank=True, help_text=b'Human-readable name of device', max_length=256, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='nas_id',
            field=models.CharField(blank=True, help_text=b'Authentication ID (propagated to the free-radius server via sadis)', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='of_id',
            field=models.CharField(blank=True, help_text=b'Logical device openflow id', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='oper_status',
            field=models.CharField(blank=True, help_text=b'operational status, whether OLT is active', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='outer_tpid',
            field=models.CharField(blank=True, help_text=b'Outer VLAN id field EtherType', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='serial_number',
            field=models.CharField(blank=True, help_text=b'Serial Number', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='switch_datapath_id',
            field=models.CharField(blank=True, help_text=b'Fabric switch to which the OLT is connected', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='switch_port',
            field=models.CharField(blank=True, help_text=b'Fabric port to which the OLT is connected', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='oltdevice_decl',
            name='uplink',
            field=models.CharField(help_text=b'uplink port, exposed via sadis', max_length=256),
        ),
        migrations.AlterField(
            model_name='onudevice_decl',
            name='admin_state',
            field=models.CharField(blank=True, choices=[(b'DISABLED', b'DISABLED'), (b'ENABLED', b'ENABLED')], default=b'ENABLED', help_text=b'admin state, whether port should be enabled', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='onudevice_decl',
            name='connect_status',
            field=models.CharField(blank=True, help_text=b'operational status, whether port is active', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='onudevice_decl',
            name='device_id',
            field=models.CharField(blank=True, help_text=b'Voltha Device ID', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='onudevice_decl',
            name='device_type',
            field=models.CharField(default=b'asfvolt16_olt', help_text=b'Device Type', max_length=256),
        ),
        migrations.AlterField(
            model_name='onudevice_decl',
            name='oper_status',
            field=models.CharField(blank=True, help_text=b'oper_status', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='onudevice_decl',
            name='serial_number',
            field=models.CharField(help_text=b'Serial number of ONU Device', max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='onudevice_decl',
            name='vendor',
            field=models.CharField(help_text=b'Vendor of ONU Device', max_length=256),
        ),
        migrations.AlterField(
            model_name='portbase_decl',
            name='admin_state',
            field=models.CharField(blank=True, help_text=b'admin state, whether port should be enabled', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='portbase_decl',
            name='name',
            field=models.CharField(db_index=True, help_text=b'Human-readable name of port', max_length=256),
        ),
        migrations.AlterField(
            model_name='portbase_decl',
            name='oper_status',
            field=models.CharField(blank=True, help_text=b'operational status, whether port is active', max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='voltservice_decl',
            name='onos_voltha_pass',
            field=models.CharField(default=b'rocks', help_text=b'The ONOS Voltha password. By default rocks', max_length=256),
        ),
        migrations.AlterField(
            model_name='voltservice_decl',
            name='onos_voltha_url',
            field=models.CharField(default=b'onos-voltha-ui.voltha.svc.cluster.local', help_text=b'The ONOS Voltha address. By default onos-voltha-ui.voltha.svc.cluster.local', max_length=256),
        ),
        migrations.AlterField(
            model_name='voltservice_decl',
            name='onos_voltha_user',
            field=models.CharField(default=b'onos', help_text=b'The ONOS Voltha username. By default sdn', max_length=256),
        ),
        migrations.AlterField(
            model_name='voltservice_decl',
            name='voltha_pass',
            field=models.CharField(default=b'admin', help_text=b'The Voltha password. By default admin', max_length=256),
        ),
        migrations.AlterField(
            model_name='voltservice_decl',
            name='voltha_url',
            field=models.CharField(default=b'voltha.voltha.svc.cluster.local', help_text=b'The Voltha API address. By default voltha.voltha.svc.cluster.local', max_length=256),
        ),
        migrations.AlterField(
            model_name='voltservice_decl',
            name='voltha_user',
            field=models.CharField(default=b'voltha', help_text=b'The Voltha username. By default voltha', max_length=256),
        ),
        migrations.AlterField(
            model_name='voltserviceinstance_decl',
            name='description',
            field=models.TextField(blank=True, help_text=b'Human-readable description', null=True),
        ),
    ]
