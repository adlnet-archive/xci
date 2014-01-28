from django import forms
from models import SystemUser

class SystemUserForm(forms.ModelForm):
	class Meta:
		password = forms.CharField(widget=forms.PasswordInput)
		widgets = {'password': forms.PasswordInput()}
		model = SystemUser
		fields = ['first_name', 'last_name', 'email', 'username', 'password']

	def save(self, commit=True):		
		# Save the provided password in hashed format
		user = super(SystemUserForm, self).save(commit=False)
		user.set_password(self.cleaned_data["password"])
		if commit:
			user.save()
		return user

class LoginForm(forms.Form):
	username = forms.CharField(max_length=200, label='Username', widget=forms.TextInput(attrs={'placeholder':'Username'}))
	password = forms.CharField(label='Password', widget=forms.PasswordInput(render_value=False, attrs={'placeholder': 'Password'}))