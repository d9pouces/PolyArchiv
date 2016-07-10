Configuration
=============

Configuration is based on standard `.ini <https://docs.python.org/3/library/configparser.html>`_ files, each file corresponding to one repository:

  * `my-local-repo.local` defines a local repository named `my-local-repo`,
  * `my-remote-repo.remote` defines a remote repository named `my-remote-repo`.

All these files are expected in the config directory `/etc/polyarchiv`. If you installed PolyArchiv in a virtualenv, this folder
is inside your virtualenv. You can also use `polyarchiv config` to display the used configuration directory, and you can change it with
the `-C` option.


Each local repository defines a base folder and one or more data sources, all of them being defined in the `my-local-repo.local` file:

  * directory with files,
  * MySQL or PostgreSQL database to dump,
  * Dovecot mails,
  * OpenLDAP database to dump.

There are several kinds of local repositories:

  * raw files,
  * local git repository: after each backup, files that have been gathered from the different sources are added and locally commited.
  * archive: all collected files are merged into a single .tar.(gz/bz2/xz) archive.

There are also several kinds of remote repositories:

  * git: the local backup is pushed to this remote git repository,
  * gitlab: almost identical to the previous one, but able to automatically create the remote repository,
  * synchronize: uses rsync to copy all files to a remote location,
  * archive: creates an archive (.tar.gz/bz2/xz) and pushes it to a remote location,
  * rolling_archive: creates an archive, pushes it to a remote location. Deletes some previous archives
    (say, one per day during six days, then one per week during three weeks, then one per month during 12 months)

These remote repositories are optional and you can of course use only local backups. All parameters (especially the remote location) can depend on the date and time, and on the hostname.

Each repository (either local or remote) is associated to a backup frequency.
If a given repository has a daily backup frequency but you execute Polyarchiv twice a day, only the first backup will be executed.

Finally, all remote repositories must store some metadata at a predictable (independant of the time and hostname) remote location (HTTP/SSH/file).
These metadata can be required for restore operations.

Local repositories
------------------

As said before, a local repository is defined in a `.ini` file written in the right configuration directory and with a name ending by `.local`.

The local repository is defined in a mandatory section `[repository]`. This local repository can a bunch of plain files, a local git repo or even an tar archive.
The main option is `engine`, defining the kind of local repository.

You must define each source of this local repository in a `[source "name_of_the_source"]` section.
Again, you must set the `engine` option, defining the kind of source.

You can also define some filters (please check the :ref:`filters` section).

.. code-block:: bash

  cat /etc/polyarchiv/my-local.local
  [repository]
  engine=git
  local_path=/tmp/local
  local_tags=local
  included_remote_tags=*
  excluded_remote_tags=
  frequency=daily

  [source "source_1"]
  engine=postgressql
  host=localhost
  port=5432
  user=test
  password=testtest
  database=testdb
  destination_path=./postgres.sql

  [source "source_2"]
  engine=mysql
  host=localhost
  port=3306
  user=test
  password=testtest
  database=testdb
  destination_path=./mysql.sql

  [source "source_3"]
  engine=rsync
  source_path=/tmp/source/files
  destination_path=./files


Remote repositories
-------------------
