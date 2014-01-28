from django.conf.urls import patterns, include, url

urlpatterns = patterns('comp.views',
	url(r'^$', 'home'),
	url(r'^logout$', 'logout_view'),
	url(r'^sign_up$', 'sign_up'),

	)