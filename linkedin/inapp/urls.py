from django.conf.urls import url
from inapp import views


urlpatterns = [
    url(r'^$', views.LinkedinSearchView.as_view(), name='search'),
    url(r'^login/$', views.LoginFormView.as_view(), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    url(r'^search-details/(?P<pk>[0-9]+)/$',
        views.SearchDetailsView.as_view(), name='search-details'),
    url(r'^run-search/$', views.make_linkedin_search, name='runsearch'),
    url(r'^restart-task/(?P<task_nmb>[0-9]+)/$',
        views.restart_task, name='restart-task'),
    url(r'^get_employees/(?P<pk>[0-9]+)/$',
        views.get_linkedin_employees_csv, name='get-employees'),
    url(r'^get_companies_list/$',
        views.get_companies_list, name='get-companies-list'),
]
