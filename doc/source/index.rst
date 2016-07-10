.. Polyarchiv documentation master file, created by

Polyarchiv
==========

Backup data from multiple local sources (organized in local repositories) and send them to one or more remote repositories.

.. code-block:: bash

       local repository 1: /var/backups/local1          /--------------------------\
       data of www.github.com               ________\__ | remote repository 1: git |
    /------------------------\             /        /   |   data of local 1        |
    |     source 1: files    |---->-------/             \--------------------------/
    |     source 2: mysql    |                          * http://mygit/backups/local1.git
    |     source 3: mysql    |---->-------\
    \------------------------/             \________\___ /-------------------------------\
                                                    /    | remote repository 2: tar+curl |
     local repository 2: : /var/backups/local2           |   data of local 1             |
     data of www.example.com                ________\___ |   data of local 2             |
    /------------------------\             /        /    \-------------------------------/
    |     source 1: files    |---->-------/             * ftp://server/backups/local1/2016-01-01.tar.gz
    |     source 2: mysql    |                          * ftp://server/backups/local2/2016-01-01.tar.gz
    \------------------------/

     local repository 3: : /var/backups/local3
     data of nothing.example.com
    /-----------------------------\
    |     source 1: files         |
    |     source 2: postgresql    |  (local backup only)
    |     source 3: mysql         |
    \-----------------------------/

You should organize your data in local repositories, each local repository having its own backup policy.
Think local repositories as projects (a website) or services (Ldap, Kerberos, …), but of course, you can organize your data as you want.

The complete backup operation is split into three steps for each local repository:

  1. collect all data from sources (databases, files, config files, …) to the local repositories,
  2. perform the local backup operation (maybe local archiving),
  3. send all these data to distant servers (you can skip this step).


.. toctree::
   :maxdepth: 1

   installation
   configuration
   examples
   locals
   remotes
   sources
   filters
   variables
   debian

