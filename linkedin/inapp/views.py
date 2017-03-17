from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.edit import FormView
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from django.http.response import JsonResponse

from inapp.models import LinkedinSearch, LinkedinSearchResult
from inapp.parser import LinkedinParser


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
    paginate_by = 3

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
    parser = LinkedinParser(search_term)
    parser.parse()

    return JsonResponse({'status': 'ok', 'parser': 'running'})
