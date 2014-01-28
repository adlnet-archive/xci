from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_protect
from django.template import RequestContext
from django.core.context_processors import csrf
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
import pdb
from .forms import SystemUserForm, LoginForm

def add_login_to_return_dict(r_dict):
	r_dict['login_form'] = LoginForm()
	return r_dict

@csrf_protect
def home(request):
	context = RequestContext(request)
	context.update(csrf(request))

	if request.method == 'GET':
		if request.user.is_authenticated():
			return render_to_response('home.html', context_instance=context)
		
		# lf = LoginForm()
		return render_to_response('home.html', add_login_to_return_dict({}), context_instance=context)
	else:
		lf = LoginForm(request.POST)

		if lf.is_valid():
			username = request.POST['username']
			password = request.POST['password']
			user = authenticate(username=username, password=password)

			if user is not None:
				login(request, user)
			else:
				return HttpResponse('Invalid login')
		else:
			return HttpResponse('Invalid login')
		return render_to_response('home.html', context_instance=context)

def logout_view(request):
	logout(request)
	return HttpResponseRedirect(reverse('comp.views.home'))

@csrf_protect
def sign_up(request):
	context = RequestContext(request)
	context.update(csrf(request))

	if request.method == 'GET':
		if request.user.is_authenticated():
			return HttpResponseRedirect(reverse('comp.views.home'))

		# lf = LoginForm()
		return_dict = {'sign_up_form': SystemUserForm(), 'hide': True}
		return render_to_response('sign_up.html', add_login_to_return_dict(return_dict), context_instance=context)
	else:
		rf = SystemUserForm(request.POST)

		if rf.is_valid():
			rf.save()
			user = authenticate(username=request.POST['username'], password=request.POST['password'])
			login(request, user)
		else:
			return HttpResponse('Invalid sign up')
		return HttpResponseRedirect(reverse('comp.views.home'))
