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
from django.contrib import messages
from django.conf import settings
from django.core.management import call_command

from inapp.models import LinkedinSearch, LinkedinSearchResult
from inapp.tasks import create_linkedin_search


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
    paginate_by = settings.ROWS_ON_PAGE

    def get_queryset(self):
        qs = super(LinkedinSearchView, self).get_queryset().order_by(
            '-date_created')
        return qs


class SearchDetailsView(LoginRequiredMixin, ListView):
    model = LinkedinSearchResult
    template_name = 'search-details.html'
    context_object_name = 'employees'
    paginate_by = settings.ROWS_ON_PAGE

    def get_queryset(self):
        return LinkedinSearchResult.objects.filter(
            search_id=self.kwargs['pk']).order_by('id')

    def get_context_data(self, **kwargs):
        data = super(SearchDetailsView, self).get_context_data(**kwargs)
        try:
            data['search_info'] = LinkedinSearch.objects.get(
                pk=self.kwargs['pk'])
        except LinkedinSearch.DoesNotExist:
            data['search_info'] = []
            messages.error(
                self.request, 'Search details does not exists in database.')

        return data


def make_linkedin_search(request):
    search_term = request.GET.get('search')
    search_type = request.GET.get('search_type')
    search_geo = request.GET.get('search_geo', None)
    create_linkedin_search.delay(search_term, search_type, search_geo)

    return JsonResponse({'status': 'success', 'msg': 'Linkedin search added'})


def restart_task(request, task_nmb):
    call_command('restart_task_with_connection_refused', task_nmb=task_nmb)

    return JsonResponse(
        {'status': 'success', 'msg': 'Task has been restarted'})


def get_linkedin_employees_csv(request, pk):
    try:
        s = LinkedinSearch.objects.get(pk=pk)
    except Exception:
        return HttpResponse('Linkedin search do not exists')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="%s_employees.csv"' % s.search_term

    writer = csv.writer(response)

    qs = LinkedinSearchResult.objects.filter(search_id=s.id).order_by('id')

    writer.writerow([
        'ID SEARCH RESULT', 'FIRST NAME', 'LAST NAME', 'TITLE', 'LOCATION'])
    for row in qs:
        first_name = row.first_name.encode(
            'utf-8').replace(';', '.') if row.first_name else None
        last_name = row.last_name.encode(
            'utf-8').replace(';', '.') if row.last_name else None
        title = row.title.encode(
            'utf-8').replace(';', '.') if row.title else None
        location = row.location.encode(
            'utf-8').replace(';', '.') if row.location else None
        current_company = row.current_company.encode(
            'utf-8').replace(';', '.') if row.current_company else None
        writer.writerow([
            row.id, first_name, last_name, title, location, current_company])

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
        result.append(line.as_dict())

    return JsonResponse({'status': 'ok', 'content': result})
