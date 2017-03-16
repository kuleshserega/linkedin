from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.edit import FormView
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib.auth import logout

from inapp.forms import EmailAuthenticationForm

from inapp.models import LinkedinSearch, LinkedinSearchResult


class LoginFormView(FormView):
    form_class = EmailAuthenticationForm
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
    paginate_by = 10

    def get_queryset(self):
        qs = super(LinkedinSearchView, self).get_queryset().order_by(
            '-date_created')
        return qs


class SearchDetailView(LoginRequiredMixin, DetailView):
    model = LinkedinSearchResult
    template_name = 'search-details.html'
    context_object_name = 'employees'
