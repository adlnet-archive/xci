xci
===

Merging the xAPI, Learning Registry and Medbiquitous competency and performance frameworks. Tested with Ubuntu 12.04.3 and Python 2.7.3

# Installation

###Software Installation

	sudo apt-get install build-essential python-dev python-virtualenv mongodb git
	sudo apt-get install libxml2-dev libxslt-dev python-dev zlib1g-dev
	sudo easy_install pip
	sudo pip install virtualenv

After you pull down your repo in the directory of your choice, create your virtual environment (don't include it in this project)

	virtualenv env

###Setup Mongo (The app uses xci as the name as the database, but you can change that in the app if you wish)
	
	mongo
	use xci

###Install packages (inside of the virtualenv you created first)

	. ./env/bin/activate
	pip install -r requirements.txt

###Add index

	mongo xci
	db.competency.ensureIndex({"title": 1})

###Add LR credentials

Whenever you link a piece of Learning Registry content to a competency/competency framework/performance framework, this system sends a paradata document back to the LR. Create a name and 
password for Node01 of the [Learning Registry](https://node01.public.learningregistry.net/apps/oauth-key-management/). Then set LR_PUBLISH_NAME and LR_PUBLISH_PASSWORD in your settings file.
You will probably want to test this out first at the [LR sandbox](https://node01.public.learningregistry.net/apps/oauth-key-management/). To publish to sandbox, the LR_PUBLISH_ENDPOINT should be https://sandbox.learningregistry.org/publish and to publish to node01, it should be https://node01.public.learningregistry.net/publish. 

###Run

	python runserver.py

	If you want run the app using gunicorn with supervisor:

		1. In xci/__init__.py comment in app.wsgi_app = ProxyFix(app.wsgi_app)
		2. In runserver.py comment out app.run(debug=True)
		3. Run supervisord


	(If you want to run the mongo shell run: mongo xci)


###Note About Common Core
	
Common Core took down the xml versions of their competencies. The app will try to load the xml if it exists on the file system.

To do this, download the cc zip [here](http://www.corestandards.org/wp-content/uploads/ccssi.zip). Extract and save one level above the project (at the same level as the env folder).

## Contributing to the project
We welcome contributions to this project. Fork this repository, make changes, and submit pull requests. If you're not comfortable with editing the code, please [submit an issue](https://github.com/adlnet/xci/issues) and we'll be happy to address it. 

## License
   Copyright &copy;2016 Advanced Distributed Learning

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
