# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError

from inapp.tasks import update_linkedin_search
from inapp.models import LinkedinSearch, STATE_CONNECTION_REFUSED, \
    STATE_TASK_RESTARTED


class Command(BaseCommand):

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--task_nmb',
            dest='task_nmb',
            default=False,
            help='Task number param',
            type=int)

    def handle(self, *args, **options):
        """Restart task with connection refused
        """
        try:
            if options['task_nmb']:
                linkedin_search = LinkedinSearch.objects.get(
                    pk=options['task_nmb'])
            else:
                linkedin_search = LinkedinSearch.objects.filter(
                    status=STATE_CONNECTION_REFUSED)
                if linkedin_search:
                    linkedin_search = linkedin_search[0]
        except Exception:
            raise CommandError('Linkedin search not found')

        linkedin_search.status = STATE_TASK_RESTARTED
        linkedin_search.save()

        update_linkedin_search.delay(linkedin_search.id)
