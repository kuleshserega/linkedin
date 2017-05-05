# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand

from inapp.tasks import create_linkedin_search
from inapp.models import LinkedinSearch, STATE_CONNECTION_REFUSED, \
    STATE_TASK_RESTARTED


class Command(BaseCommand):

    def handle(self, *args, **options):
        """Restart task with connection refused
        """
        linkedin_search = LinkedinSearch.objects.filter(
            status=STATE_CONNECTION_REFUSED)
        if linkedin_search:
            linkedin_search = linkedin_search[0]
            linkedin_search.status = STATE_TASK_RESTARTED
            linkedin_search.save()

            search_geo = None
            if linkedin_search.search_geo:
                search_geo = linkedin_search.search_geo

            create_linkedin_search.delay(
                linkedin_search.search_term,
                linkedin_search.search_type,
                search_geo)
