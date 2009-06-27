Nose django helper plugin
=========================

With this plugin you can write standard Nose unit tests inside a
Django application.

The plugin takes care of finding your applications settings.py file
and creating/tearing down test database. It also has support for
fixtures and it has experimental mechanism that wraps the tests in
transactions to speed up testing.

This plugin has been tested with Django 1.0-branch. It probably works
with 1.1.

Usage
-----

Unit tests can be run with following command::

  nose-django --with-django [nose-options]

Custom settings be used by setting ``DJANGO_SETTINGS_MODULE``
environmental variable.

Building Debian package
-----------------------

Plugin can also be installed as a Debian package::

  dpkg-checkbuilddeps
  dpkg-buildpackage -us -uc -rfakeroot
  sudo debi

Authors
-------

This version is maintained by Jyrki Pulliainen
<jyrki.pulliainen@inoi.fi>.

Original plugin courtesy of Victor Ng <crankycoder@gmail.com> who
rewrote Jason Pellerin's original nose-django plugin.
