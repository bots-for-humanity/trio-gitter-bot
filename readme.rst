Gitter Bot for Python-Trio project
==================================

Watch for new questions in stackoverflow tagged with ``python-trio``, and post it
to `Python Trio's Gitter channel <https://gitter.im/python-trio/general>`_.

How it works
------------

1. Run as a scheduled task every 10 minutes.

2. Read the RSS feed at https://stackoverflow.com/feeds/tag?tagnames=python-trio&sort=newest .

3. If there is post newer than 10 minutes ago, post that to `Gitter <https://gitter.im/python-trio/general>`_.

About the bot
-------------

This bot was heavily inspired by `gidgethub <https://gidgethub.readthedocs.io>`_ and CPython's GitHub bots.



