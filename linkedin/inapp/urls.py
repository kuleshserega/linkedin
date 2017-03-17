from django.conf.urls import url
from inapp import views


urlpatterns = [
    url(r'^$', views.LinkedinSearchView.as_view(), name='search'),
    url(r'^login/$', views.LoginFormView.as_view(), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    url(r'^search-details/(?P<pk>[0-9]+)/$',
        views.SearchDetailsView.as_view(), name='search-details'),
    url(r'^run-search/$', views.make_linkedin_search, name='runsearch'),
]
