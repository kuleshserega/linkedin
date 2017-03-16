from django.conf.urls import url
from inapp import views


urlpatterns = [
    url(r'^$', views.LinkedinSearchView.as_view(), name='search'),
    url(r'^login/$', views.LoginFormView.as_view(), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    url(r'^search-results/(?P<pk>[0-9]+)/$',
        views.SearchDetailView.as_view(),
        name='search_results'),
]
