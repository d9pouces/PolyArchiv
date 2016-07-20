Configuration
=============

Configuration is based on standard `.ini <https://docs.python.org/3/library/configparser.html>`_ files, each file corresponding to one repository:

  * `my-collect-point.collect` defines a collect point named `my-collect-point`,
  * `my-backup-point.backup` defines a backup point named `my-backup-point`.

All these files are expected in the config directory `/etc/polyarchiv`. If you installed PolyArchiv in a virtualenv, this folder
is inside your virtualenv. You can also use `polyarchiv config` to display the actual configuration directory, and you can change it with
the `-C` option.


Each collect point defines a base folder and one or more data sources, all of them being defined in the `my-collect-point.collect` file:

  * directory with files,
  * MySQL or PostgreSQL database to dump,
  * Dovecot mails,
  * OpenLDAP database to dump.

There are several kinds of collect points:

  * raw files,
  * git repository: after each backup, files that have been gathered from the different sources are added and locally commited.
  * archive: all collected files are merged into a single .tar.(gz/bz2/xz) archive.

There are also several kinds of backup points:

  * git: the local backup is pushed to this remote git repository,
  * gitlab: almost identical to the previous one, but able to automatically create the backup point,
  * synchronize: uses rsync to copy all files to a remote location,
  * archive: creates an archive (.tar.gz/bz2/xz) and pushes it to a remote location,
  * rolling_archive: creates an archive, pushes it to a remote location. Deletes some previous archives
    (say, one per day during six days, then one per week during three weeks, then one per month during 12 months)

These backup points are optional and you can of course use only local collect points, for example when your collect point is stored on a NFS share. All parameters (especially the remote location) can depend on the date and time, and on the hostname.

Any collect/backup point can be associated to a backup frequency:
if a given repository has a daily backup frequency but you execute Polyarchiv twice a day, only the first backup will be executed.
If no frequency is set, then the backup is performed every time you launch polyarchiv.

collect points
--------------

As said before, a collect point is defined by a `ini` file in the configuration directory and with a name ending by `.collect`.

The collect point is defined in a mandatory section `[repository]`. This collect point can a bunch of plain files, a local git repo or even an tar archive.
The main option is `engine`, defining the kind of collect point. The complete list of the available kinds is here: :ref:`collect_points`.

You must define each source of this collect point in a `[source "name_of_the_source"]` section.
Again, you must set the `engine` option, defining the kind of source. Please check the list of available sources: :ref:`sources`.

You can also define some filters for transforming files (please check the :ref:`filters` section).

.. code-block::  ini
  :caption: /etc/polyarchiv/my-collect-point.collect

  [repository]
  engine=git
  local_path=/tmp/local
  collect_point_tags=local
  included_backup_point_tags=*
  excluded_backup_point_tags=
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

Backup points
-------------

As said before, a backup point is defined by a `ini` file in the configuration directory and with a name ending by `.backup`.
This config file requires a mandatory section `[repository]`.
The main option is `engine`, defining the kind of backup points. Please check the list of available backup points: :ref:`backup_points`.

By default, all backup points are used with all collect points. Therefore, you should use at least the `name`
variable (the  name of the collect point) to backup several collect points with the same backup point.
Please check the section :ref:`variables` for a more detailed explanation.

.. _urls:

URLs
----

Excepting git URLs, valid URLs must look like one of these examples:
  * `file:///foo/bar/baz` for direct file operation,
  * `ssh://username@hostname/boo/bar/baz`, but `keytab` or `private_key` must be set,
  * `http(s)://username:password@hostname/foo/bar/baz.git`, you can set `ca_cert` to the private root certificate or to `"any"` for accepting self-signed certificates.
  * `http(s)://:@hostname/foo/bar/baz.git` and `private_key` for certificate auth

Of course, `http`-like URLs require a WebDAV-compliant server (you can use Apache or Nginx).

Git remote URLs must look like:
  * `file:///foo/bar/baz.git`,
  * `git@hostname/foo/bar/baz.git` (and `private_key` must be set),
  * `http(s)://username:password@hostname/foo/bar/baz.git`,
  * `http(s)://x:x@hostname/foo/bar/baz.git` (if `keytab` set; note the `x:x@`!).

.. warning::

  The first SSH connection can fail if the destination is unknown. Be sure you have either `StrictHostKeyChecking no` in
  your SSH configuration file, or (safer choice) the remote server is known.

.. _remote_metadata:

Remote metadata storage
-----------------------

Most parameters for backup points can rely on time-based, or host-based, variables: for example,
`remote_url = ssh://example.org/backups/{hostname}/{name}-{Y}-{m}.tar.gz`.
If you restore your data on a brand new machine, there is no way to determine the previous `hostname`, nor
the time of the last backup (the `Y` and `m` values).
So, if your remote parameters depend on such variables, you should use the `metadata_url` parameter, allowing to
store (and retrieve!) these data to a predictible location.
This URL should either depend on the `name` variable or ends by `/` (allowing to append `{name}.json`).

Associating collect and backup points
-------------------------------------

All backup points apply to all collect points but you can change this behaviour by applying tags to repositories.
By default, a collect point has the tag `collect` and include all existing backup points: `included_backup_point_tags=*`.
A backup point has the tag `backup` and include all collect points: `included_collect_point_tags=*`.

If large collect points should not be sent to a given backup point, you can exclude the "large" tags from the backup configuration:

.. code-block::  ini
  :caption: /etc/polyarchiv/my-backup-point.backup
  :name: tags1:/etc/polyarchiv/my-backup-point.backup

  [repository]
  engine=git
  excluded_collect_point_tags=*large,huge

and add the `large` tag to the local configuration you want to avoid
(traditionnal shell expansion with ? and * is used for comparing included and excluded tags, so you can put `extra-large`
instead of simply `large`):

.. code-block:: ini
  :caption: /etc/polyarchiv/my-collect-point.collect
  :name: tags1:/etc/polyarchiv/my-collect-point.collect

  [repository]
  engine=git
  local_path=/tmp/local
  collect_point_tags=local,extra-large


Tags can also be applied to backup points:

.. code-block:: ini
  :caption: /etc/polyarchiv/my-backup-point.backup
  :name: tags:/etc/polyarchiv/my-backup-point.backup

  [repository]
  engine=git
  backup_point_tags=small-only

and add the "large" tag to the local configuration:

.. code-block::  ini
  :caption: /etc/polyarchiv/my-collect-point.collect
  :name: tags:/etc/polyarchiv/my-collect-point.collect

  [repository]
  engine=git
  local_path=/tmp/local
  included_backup_point_tags=huge,large

Since the backup point does not present either the `huge` tag or the `large` tag, it will not be applied.
