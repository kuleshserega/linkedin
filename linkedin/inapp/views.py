# -*- coding: UTF-8 -*-
import csv

from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.edit import FormView
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from django.http.response import JsonResponse
from django.core.urlresolvers import reverse
from django.conf import settings

from inapp.models import LinkedinSearch, LinkedinSearchResult
from inapp.tasks import create_linkedin_search
from templatetags.base_extra import status_icons


class LoginFormView(FormView):
    form_class = AuthenticationForm
    template_name = "login.html"
    success_url = "/"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return HttpResponseRedirect('/')
        else:
            return super(LoginFormView, self).dispatch(
                request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.get_user())
        return super(LoginFormView, self).form_valid(form)


class LogoutView(View):
    def get(self, request):
        logout(request)
        return HttpResponseRedirect("/login")


class LinkedinSearchView(LoginRequiredMixin, ListView):
    model = LinkedinSearch
    template_name = 'search.html'
    context_object_name = 'results'
    paginate_by = 15

    def get_queryset(self):
        qs = super(LinkedinSearchView, self).get_queryset().order_by(
            '-date_created')
        return qs


class SearchDetailsView(LoginRequiredMixin, ListView):
    model = LinkedinSearchResult
    template_name = 'search-details.html'
    context_object_name = 'employees'
    paginate_by = 15

    def get_queryset(self):
        return LinkedinSearchResult.objects.filter(search_id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        data = super(SearchDetailsView, self).get_context_data(**kwargs)
        try:
            data['search_info'] = LinkedinSearch.objects.get(
                pk=self.kwargs['pk'])
        except Exception:
            print('Search not exists in database')

        return data


def make_linkedin_search(request):
    search_term = request.GET.get('search')
    create_linkedin_search.delay(search_term)

    return JsonResponse({'status': 'ok', 'parser': 'running'})


def get_linkedin_employees_csv(request, pk):
    try:
        s = LinkedinSearch.objects.get(pk=pk)
    except Exception:
        return HttpResponse('Linkedin search do not exists')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="%s_employees.csv"' % s.search_company

    writer = csv.writer(response)

    qs = LinkedinSearchResult.objects.filter(search_id=s.id)

    writer.writerow(['ID SEARCH RESULT', 'FULL NAME', 'TITLE'])
    for row in qs:
        writer.writerow([
            row.id,
            row.full_name.encode('utf-8').replace(';', '.'),
            row.title.encode('utf-8').replace(';', '.')])

    return response


def get_companies_list(request):
    page = request.GET.get('page')
    page = int(page) if page else 1
    start = 0
    if page > 1:
        start = page*settings.ROWS_ON_PAGE - settings.ROWS_ON_PAGE
    end = page*settings.ROWS_ON_PAGE
    qs = LinkedinSearch.objects.all().order_by(
            '-date_created')[start:end]

    result = []
    for line in qs:
        date_created = line.date_created.strftime("%Y-%m-%d %H:%M:%S")
        result.append({
            'id': line.id,
            'search_company': line.search_company,
            'date_created': date_created,
            'companyId': line.companyId,
            'status_text': line.get_status_display(),
            'status_icon': status_icons(line.status),
            'search_details_url': reverse(
                'inapp:search-details', kwargs={'pk': line.id}),
            'employees_to_csv': reverse(
                'inapp:get-employees', kwargs={'pk': line.id}),
        })

    return JsonResponse({'status': 'ok', 'content': result})
