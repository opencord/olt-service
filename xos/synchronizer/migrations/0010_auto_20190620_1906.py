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
# Generated by Django 1.11.21 on 2019-06-20 23:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('volt', '0009_auto_20190610_1723'),
    ]

    operations = [
        migrations.AddField(
            model_name='oltdevice_decl',
            name='technology',
            field=models.CharField(choices=[(b'gpon', b'gpon'), (b'xgspon', b'xgspon')], db_index=True, default=b'xgspon', help_text=b'The technology being utilized by the adapter', max_length=16),
        ),
        migrations.AlterUniqueTogether(
            name='technologyprofile_decl',
            unique_together=set([('profile_id', 'technology')]),
        ),
    ]