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
STATE_ASKS_CODE = 6
STATE_CODE_NOT_VALID = 7
STATE_LINKEDIN_USER_EMPTY = 8
STATE_ASKS_PREMIUM = 9
STATE_CONNECTION_REFUSED = 10
STATE_TASK_RESTARTED = 11


STATUS_CHOICES = (
    (STATE_IN_PROCESS, _('Search in process')),
    (STATE_FINISHED, _('Search is finished')),
    (STATE_ERROR, _('Search has errors')),
    (STATE_NOT_LOGGED_IN, _('Linkedin user is not logged in')),
    (STATE_AUTHENTICATED, _('Linkedin user has been authenticated')),
    (STATE_ASKS_CODE, _('Linkedin asks verification code')),
    (STATE_CODE_NOT_VALID, _('Linkedin verification code is not valid')),
    (STATE_LINKEDIN_USER_EMPTY, _('No linkedin user was added to the db')),
    (STATE_ASKS_PREMIUM, _('Linkedin asks premium')),
    (STATE_CONNECTION_REFUSED, _('Connection refused')),
    (STATE_TASK_RESTARTED, _('Task has been restarted')),
)

SEARCH_BY_COMPANY = 1
SEARCH_BY_GEO = 2

SEARCH_TYPE_CHOICES = (
    (SEARCH_BY_COMPANY, _('Search by company or company ID')),
    (SEARCH_BY_GEO, _('Search by Geo'))
)


class LinkedinSearch(models.Model):
    search_term = models.CharField(
        default=None, null=True, blank=True,
        max_length=120, verbose_name=_('Search term'))
    companyId = models.IntegerField(
        default=None, null=True, blank=True,
        verbose_name=_('Linkedin company ID'))
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date created'))
    status = models.SmallIntegerField(
        default=1, choices=STATUS_CHOICES, verbose_name=_('Status of search'))
    search_type = models.SmallIntegerField(
        default=1, choices=SEARCH_TYPE_CHOICES, verbose_name=_('Search type'))
    search_geo = models.CharField(
        default=None, null=True, blank=True,
        max_length=120, verbose_name=_('Search geo location'))

    def as_dict(self):
        date_created = self.date_created.strftime("%Y-%m-%d %H:%M:%S")
        result = {
            'id': self.id,
            'search_term': self.search_term,
            'date_created': date_created,
            'companyId': self.companyId,
            'search_geo': self.search_geo,
            'search_type': self.get_search_type_display(),
            'status': self.status,
            'status_text': self.get_status_display(),
            'status_icon': status_icons(self.status),
            'search_details_url': reverse(
                'inapp:search-details', kwargs={'pk': self.id}),
            'employees_to_csv': reverse(
                'inapp:get-employees', kwargs={'pk': self.id}),
        }
        return result

    def __str__(self):
        return self.search_term


class LinkedinSearchResult(models.Model):
    first_name = models.CharField(
        default=None, null=True, blank=True,
        max_length=120, verbose_name=_('First name'))
    last_name = models.CharField(
        default=None, null=True, blank=True,
        max_length=120, verbose_name=_('Last name'))
    title = models.CharField(
        default=None, null=True, blank=True,
        max_length=250, verbose_name=_('Title'))
    current_company = models.CharField(
        default=None, null=True, blank=True,
        max_length=250, verbose_name=_('Current company'))
    location = models.CharField(
        default=None, null=True, blank=True,
        max_length=250, verbose_name=_('Location'))
    search = models.ForeignKey(
        'LinkedinSearch', verbose_name=_('Linkedin Search instance'))

    def __str__(self):
        last_name = self.last_name
        if not self.last_name:
            last_name = ''
        return "%s %s" % (self.first_name, last_name)

    def __unicode__(self):
        return unicode(self.id)


class LinkedinUser(models.Model):
    email = models.CharField(
        max_length=120, verbose_name=_('Linkedin email'))
    password = models.CharField(
        max_length=120, verbose_name=_('Linkedin password'))
    verification_code = models.CharField(
        default=None, null=True, blank=True, max_length=30,
        verbose_name=_('Linkedin verification code'))

    def __str__(self):
        return self.email
