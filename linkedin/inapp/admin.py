from django.contrib import admin

from inapp.models import LinkedinSearch, LinkedinSearchResult, \
    LinkedinUser

admin.site.register(LinkedinSearch)
admin.site.register(LinkedinSearchResult)
admin.site.register(LinkedinUser)
