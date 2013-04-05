ODKScan_webapp
--------------------------------------------------------------------------------

A Django app interface for ODK Scan

Starting from the VM Image:
--------------------------------------------------------------------------------

1. Log in with username "user" and password "password"
2. Go to the users view and create a new users with your desired username and password.
3. On the next screen give yourself superuser and staff status.
4. Now delete the default "user" and log in with your new account.

Full setup directions:
--------------------------------------------------------------------------------

Start with 32bit ubuntu 12.04 LTS

### Install these dependencies:

```bash
sudo apt-get update 
sudo apt-get install git python-imaging
```

### Install OpenCV:

```bash
sudo apt-get install libopencv-dev
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
```

### Install Django:

```bash
sudo easy_install pip
#You may want to set this to version 1.5.1 in case later versions
#have any backwards compatibility issues.
#Don't try to user a version earlier than 1.4.0
sudo pip install django
sudo pip install docutils
```

### Create the project:

```bash
django-admin.py startproject scan_admin
cd scan_admin
git clone git://github.com/UW-ICTD/ODKScan_webapp.git --recursive
#If this was forked you might need to alter the UW-ICTD part.
```

### Install the webapp's pip dependencies:

```bash
cd ODKScan_webapp
sudo pip install -r requirements.pip
```

### Configure the scan_admin project's settings.py:

* Set MEDIA_ROOT to an absolute path, e.g.:
`/home/ubuntu/scan_admin/media/`
* Set MEDIA_URL to a path beginning with a slash, e.g.: `/media/`
* set database engine to sqlite3 and name it with an _absolute_ path, e.g.:
`/home/ubuntu/scan_admin/scan.db`
* Add "ODKScan_webapp" to INSTALLED_APPS and uncomment the admin entries.

### Configure the scan_admin project's urls.py:

* Uncomment all the admin stuff.
* Paste the following at the bottom of the file:

```python
urlpatterns += [url(r'', include('ODKScan_webapp.urls'))]

#This to serve static media. For production servers you aren't supposed to serve media with Django.
from django.conf import settings
if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()

urlpatterns += [url(r'^accounts/', include('django.contrib.auth.urls'))]
```

### Initialize the database:

This command will also prompt you to set up a super user account.

```bash
python manage.py syncdb
```

## Run the app using a apache mod-wsgi server

Install the necessairy packages:

```bash
sudo apt-get install apache2 libapache2-mod-wsgi
```

Edit your httpd.conf file like so:

```bash
sudo pico /etc/apache2/httpd.conf
```
so that it contains this:

```xml
#Need to set the apache user so we have permissions to write/access files.
User ubuntu
Group ubuntu

WSGIScriptAlias / /home/ubuntu/scan_admin/scan_admin/wsgi.py
WSGIPythonPath /home/ubuntu/scan_admin
#A bunch of stuff to make the server run in daemon mode, which is better.
WSGIApplicationGroup scan_admin
WSGIDaemonProcess scan_admin user=ubuntu group=ubuntu threads=10 maximum-requests=100 python-path=/home/ubuntu/scan_admin shutdown-timeout=100
WSGIProcessGroup scan_admin
WSGIRestrictEmbedded On

<Directory /home/ubuntu/scan_admin/scan_admin>
#if enabled allows cors requests from github hosted apps.
#SetEnvIf Origin "^(.*[(github\.com)(c9\.io)])$" ORIGIN_SUB_DOMAIN=$1
#Header set Access-Control-Allow-Origin "%{ORIGIN_SUB_DOMAIN}e" env=ORIGIN_SUB_DOMAIN
<Files wsgi.py>
Order deny,allow
Allow from all
</Files>
</Directory>
```

Now restart the server for changes to take effect.

```bash
sudo /etc/init.d/apache2 restart
```

### Alternative way to run the server:

It might be easier to [use gunicorn to run the server](http://adrian.org.ar/django-nginx-green-unicorn-in-an-ubuntu-11-10-ec2-instance/):

```bash
sudo apt-get install gunicorn
cd scan_admin
#Use killall gunicorn_django to stop the server
sudo gunicorn_django -b 0.0.0.0:80 --daemon -w 4
```

The reason I prefer the apache setup I documented is that I have some experience
using it in the past and the server automatically starts when the machine reboots.

Architecture
--------------------------------------------------------------------------------

* The django code in admin.py and models.py configures what's in the admin interface.
* actions.py contains code for processing forms with ODK Scan, rendering transcription pages and generating csvs.
* The ODKScan-core contains the image processing code.
* The UI for the transcription interfaces is contained in static/transcription and in the templates directory.
