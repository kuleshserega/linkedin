from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from templatetags.base_extra import status_icons

STATE_IN_PROCESS = 1
STATE_FINISHED = 2
STATE_ERROR = 3
STATE_NOT_LOGGED_IN = 4
STATE_AUTHENTICATED = 5
STATE_NOT_VALID_CODE = 6


STATUS_CHOICES = (
    (STATE_IN_PROCESS, _('Search in process')),
    (STATE_FINISHED, _('Search is finished')),
    (STATE_ERROR, _('Search has errors')),
    (STATE_NOT_LOGGED_IN, _('Linkedin user is not logged in')),
    (STATE_AUTHENTICATED, _('Linkedin user has been authenticated')),
    (STATE_NOT_VALID_CODE, _('Linkedin verification code is not valid')),
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

    def as_dict(self):
        date_created = self.date_created.strftime("%Y-%m-%d %H:%M:%S")
        result = {
            'id': self.id,
            'search_company': self.search_company,
            'date_created': date_created,
            'companyId': self.companyId,
            'status_text': self.get_status_display(),
            'status_icon': status_icons(self.status),
            'search_details_url': reverse(
                'inapp:search-details', kwargs={'pk': self.id}),
            'employees_to_csv': reverse(
                'inapp:get-employees', kwargs={'pk': self.id}),
        }
        return result


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
    verification_code = models.CharField(
        default=None, null=True, max_length=30,
        verbose_name=_('Linkedin verification code'))
