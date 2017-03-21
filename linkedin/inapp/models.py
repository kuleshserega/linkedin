from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

STATE_IN_PROCESS = 1
STATE_FINISHED = 2
STATE_ERROR = 3

STATUS_CHOICES = (
    (STATE_IN_PROCESS, _('Search in process')),
    (STATE_FINISHED, _('Search is finished')),
    (STATE_ERROR, _('Search has errors')),
)


class LinkedinSearch(models.Model):
    search_company = models.CharField(
        max_length=120, verbose_name=_('Search term'))
    companyId = models.IntegerField(
        default=None, null=True, verbose_name=_('Linkedin company ID'))
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date created'))
    status = models.SmallIntegerField(
        default=1, choices=STATUS_CHOICES, verbose_name=_('Status of search'))


class LinkedinSearchResult(models.Model):
    full_name = models.CharField(
        max_length=120, verbose_name=_('Full name'))
    title = models.CharField(
        max_length=250, verbose_name=_('Title'))
    search = models.ForeignKey(
        'LinkedinSearch', verbose_name=_('Linkedin Search instance'))


class LinkedinUser(models.Model):
    email = models.CharField(
        max_length=120, verbose_name=_('Linkedin email'))
    password = models.CharField(
        max_length=120, verbose_name=_('Linkedin password'))
