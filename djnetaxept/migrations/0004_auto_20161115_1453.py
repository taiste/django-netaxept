# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-15 14:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djnetaxept', '0003_auto_20161110_1304'),
    ]

    operations = [
        migrations.AlterField(
            model_name='netaxepttransaction',
            name='operation',
            field=models.CharField(choices=[(b'AUTH', b'AUTH'), (b'SALE', b'SALE'), (b'CAPTURE', b'CAPTURE'), (b'CREDIT', b'CREDIT'), (b'ANNUL', b'ANNUL'), (b'VERIFY', b'VERIFY')], max_length=7),
        ),
    ]
