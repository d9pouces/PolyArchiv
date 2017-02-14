.. Polyarchiv documentation master file, created by

Polyarchiv
==========

Backup data from multiple local "sources" (organized in "collect points") and send them to one or more "backup points".

.. code-block:: bash

       collect point 1: /var/backups/local1             /---------------------------\
       data of dev.example.com              ________\__ |   backup point 1: git     |
    /------------------------\             /        /   |   data of collect point 1 |
    |     source 1: files    |---->-------/             \---------------------------/
    |     source 2: mysql    |                          * http://mygit/backups/local1.git
    |     source 3: mysql    |---->-------\
    \------------------------/             \________\___ /-------------------------------\
                                                    /    |   backup point 2: tar+curl    |
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

  1. collect all data from sources (like copying files or dumping databases) to the collect point,
  2. perform the local collect operation (maybe a local `tar.gz` archive, or just keep collected files as-this),
  3. optionally send all the collected data to one or more distant servers.

Some filters can be used (currently encrypting files or computing their md5 hashes) between the local collect and the remote send.
Extra actions (“hooks”) can be called before or after a backup, or in case of success/error.

.. toctree::
   :maxdepth: 1

   quickstart
   installation
   options
   configuration
   examples
   collect_points
   backup_points
   sources
   filters
   hooks
   variables
   global

