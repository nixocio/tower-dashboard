[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# Tower QE Dashboard

A set of Tower QE dashboard that allows to have better insight of what is going on

## Install

### Setting up Fedora to build the production RPMs

In order to build the production RPM you need to install the following
packages:

```console
$ sudo dnf install mock rpm-build rpmdevtools
```

Then add your user to the mock group:

```console
$ sudo usermod -a -G mock "${USER}"
```

After that you can proceed to the initial production deployment if you
deploying to production for the first time, or updating production deployment
if you are updating an existing production environment.

Note: this was tested on Fedora 30.

### Initial Production Deployment

To be able to setup a production environment, few steps are required.

  1. Locally build the `tower-dashboard` rpm. (Mock needs to be previously installed)

  ```bash
  #> ./contrib/packaging/build_rpm.sh
  ```

  2. By default, the script above will place the resulting RPM on `/tmp`. That
     said, scp the resulting RPM package to the production system, for example:

  ```console
  $ scp /tmp/tower-dashboard-*.noarch.rpm user@remotehost:
  ```

  3. On the production server

  ```bash
  #> yum -y install httpd mod_wsgi epel-release
  #> yum -y install python-pip
  #> yum -y install /path/to/tower-dashboard.rpm
  #> pip install -U flask
  ```

  4. Create the proper httpd configuration (`/etc/httpd/conf.d/00_dashboard,conf`)

  ```
  <VirtualHost *:80>
    CustomLog logs/tower_dashboard combined
    ErrorLog logs/tower_dashboar_errors
    DocumentRoot /usr/share/tower-dashboard

    WSGIScriptAlias / /usr/share/tower-dashboard/wsgi.py
    WSGIPassAuthorization On

    <Directory /usr/lib/python2.7/site-packages/towerdashboard>
       AllowOverride None
       Require all granted
    </Directory>

    <Directory /usr/share/tower-dashboard>
       AllowOverride None
       Require all granted
    </Directory>
  </VirtualHost>
  ```

 5. Edit `/etc/tower-dashboard/settings.py`

 6. Restart httpd

### Updating Production Deployment

To be able to update a production environment, few steps are required:

  1. Locally build the `tower-dashboard` rpm. See previous section for more information.

  2. By default, the script above will place the resulting RPM on `/tmp`. That
     said, scp the resulting RPM package to the production system, for example:

  ```console
  $ scp /tmp/tower-dashboard-*.noarch.rpm user@remotehost:
  ```

  3. On the production server install the updated RPM:

  ```bash
  #> yum -y install /path/to/updated-tower-dashboard.rpm
  ```

  4. Remove/rename old database. Be aware that the default path to the database
     is on `/tmp/towerdashboard.sqlite` but since on production it is running
     on httpd managed by systemd, then the database path may end up being
     something like `/tmp/systemd-private-*-httpd.service-*/tmp/towerdashboard.sqlite`.

  5. Restart httpd

### Development

To be able to set up a dev environment, few steps are required.

  1. Ensure `pip` and `virtualenv` are installed

  ```bash
  #> yum -y install python-pip python-virtualenvironment
  ```

  2. Create yourself a virtual environment

  ``` bash
  #> virtualenv /path/to/towerdasboard/venv
  #> source /path/to/towerdashboard/venv/bin/activate
  ```

  3. Clone the repository

  ``` bash
  #> git clone https://github.com/Spredzy/tower-dashboard
  ```

  4. Install the dependencies

  ``` bash
  #> cd tower-dashboard
  #> pip install -r requirements.txt
  ```

  5. Copy and edit the settings.sample.py file

  ``` bash
  #> cp settings.sample.py /tmp/settings.py
  #> vim /tmp/settings.py
  ```

  5. Rock'n'Roll

  ``` bash
  #> FLASK_APP=/path/to/towerdashboard/app.py FLASK_DEBUG=1 TOWERDASHBOARD_SETTINGS=/tmp/settings.py flask run
  ```

  6. Initialize the DB
  ```
  #> curl http://127.0.0.1:5000/init-db
  ```

tower-dashboard should be running on your local loop on port 5000 (`http://127.0.0.1:5000`)


## License

Apache 2.0


## Contact

  * Tower QE  <ansible-tower-qe@redhat.com>
