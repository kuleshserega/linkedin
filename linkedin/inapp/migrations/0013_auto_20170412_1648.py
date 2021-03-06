# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-12 16:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inapp', '0012_auto_20170411_1458'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='linkedinsearch',
            name='geo',
        ),
        migrations.AddField(
            model_name='linkedinsearch',
            name='search_type',
            field=models.SmallIntegerField(choices=[(1, 'Search in process'), (2, 'Search is finished'), (3, 'Search has errors'), (4, 'Linkedin user is not logged in'), (5, 'Linkedin user has been authenticated'), (6, 'Linkedin asks verification code'), (7, 'Linkedin verification code is not valid'), (8, 'No linkedin user was added to the db'), (9, 'Linkedin asks premium')], default=1, verbose_name='Search type'),
        ),
    ]
