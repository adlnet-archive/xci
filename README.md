xci
===

#### Merging the xAPI, Learning Registry and Medbiquitous competency and performance frameworks. Tested with Ubuntu 12.04.3 and Python 2.7.3

## Installation

Software Installation

	sudo apt-get install build-essential python-dev python-virtualenv mongodb git
	sudo easy_install pip
	sudo pip install virtualenv

After you pull down your repo in the directory of your choice, create your virtual environment (don't include it in this project)

	virtualenv env

Setup Mongo (The app uses xci as the name as the database, but you can change that in the app if you wish)
	
	mongo
	use xci

Install packages (inside of the virtualenv you created first)

	. ./env/bin/activate
	pip install -r requirements.txt

Add index

	mongo xci
	db.competency.ensureIndex({"title": 1})

Run

	python runserver.py

	If you want run the app using gunicorn with supervisor:

		1. In xci/__init__.py comment in app.wsgi_app = ProxyFix(app.wsgi_app)
		2. In runserver.py comment out app.run(debug=True)
		3. Run supervisord


	(If you want to run the mongo shell run: mongo xci)


Note About Common Core
	
Common Core took down the xml versions of their competencies. The app will try to load the xml if it exists on the file system.

To do this, download the cc zip [here](http://www.corestandards.org/wp-content/uploads/ccssi.zip). Extract and save one level above the project (at the same level as the env folder).
