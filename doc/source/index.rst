.. Polyarchiv documentation master file, created by

Polyarchiv
==========

Backup data from multiple local sources (organized in collect points) and send them to one or more remote repositories.

.. code-block:: bash

       collect point 1: /var/backups/local1             /---------------------------\
       data of www.github.com               ________\__ | remote repository 1: git  |
    /------------------------\             /        /   |   data of collect point 1 |
    |     source 1: files    |---->-------/             \---------------------------/
    |     source 2: mysql    |                          * http://mygit/backups/local1.git
    |     source 3: mysql    |---->-------\
    \------------------------/             \________\___ /-------------------------------\
                                                    /    | remote repository 2: tar+curl |
     collect point 2: : /var/backups/local2              |   data of collect point 1     |
     data of www.example.com                ________\___ |   data of collect point 2     |
    /------------------------\             /        /    \-------------------------------/
    |     source 1: files    |---->-------/             * ftp://server/backups/local1/2016-01-01.tar.gz
    |     source 2: mysql    |                          * ftp://server/backups/local2/2016-01-01.tar.gz
    \------------------------/

     collect point 3: : /var/backups/local3
     data of nothing.example.com
    /-----------------------------\
    |     source 1: files         |
    |     source 2: postgresql    |  (local backup only)
    |     source 3: mysql         |
    \-----------------------------/

You should organize your data in collect points, each collect point having its own backup policy.
Think collect points as projects (a website) or services (Ldap, Kerberos, …), but of course, you can organize your data as you want.


The complete backup operation is split into three steps for each collect point:

  1. collect all data from sources (databases, files, config files, …) to the collect points,
  2. perform the local collect operation (maybe a local `git` archive, or just raw files),
  3. send all these data to distant servers (you can of course skip this step).


.. toctree::
   :maxdepth: 1

   quickstart
   installation
   options
   configuration
   examples
   collect_points
   remotes
   sources
   filters
   variables
   debian

