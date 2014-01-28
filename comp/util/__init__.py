from django.contrib.admin.sites import AlreadyRegistered
from django.db.models import get_models, get_app
from django.contrib import admin

def autoregister(*app_list):
	for app_name in app_list:
		app_models = get_app(app_name)
		for model in get_models(app_models):
			try:
				admin.site.register(model)
			except AlreadyRegistered:
				pass 