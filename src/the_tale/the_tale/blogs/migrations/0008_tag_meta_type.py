# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2019-11-23 08:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0007_auto_20161019_1613'),
    ]

    operations = [
        migrations.AddField(
            model_name='tag',
            name='meta_type',
            field=models.IntegerField(blank=True, choices=[('', '----')], default=None, null=True),
        ),
    ]