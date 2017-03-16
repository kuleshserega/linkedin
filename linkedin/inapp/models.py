from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _


class LinkedinSearch(models.Model):
    search_company = models.CharField(
        max_length=120, verbose_name=_('Search term'))
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date created'))


class LinkedinSearchResult(models.Model):
    full_name = models.CharField(
        max_length=120, verbose_name=_('Full name'))
    title = models.CharField(
        max_length=250, verbose_name=_('Title'))
    search = models.ForeignKey(
        'LinkedinSearch', verbose_name=_('Linkedin Search instance'))
