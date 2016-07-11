Configuration
=============

Configuration is based on standard `.ini <https://docs.python.org/3/library/configparser.html>`_ files, each file corresponding to one repository:

  * `my-local-repo.local` defines a local repository named `my-local-repo`,
  * `my-remote-repo.remote` defines a remote repository named `my-remote-repo`.

All these files are expected in the config directory `/etc/polyarchiv`. If you installed PolyArchiv in a virtualenv, this folder
is inside your virtualenv. You can also use `polyarchiv config` to display the actual configuration directory, and you can change it with
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

These remote repositories are optional and you can of course use only local backups.
Several remote parameters (especially the remote location) can depend on the date/time or the hostname (check the remote doc for more information).

Each repository (either local or remote) can be associated to a backup frequency:
if a given repository has a daily backup frequency but you execute Polyarchiv twice a day, only the first backup will be executed.
If no frequency is set, then the backup is performed every time you launch polyarchiv.

Local repositories
------------------

As said before, a local repository is defined by a `ini` file in the configuration directory and with a name ending by `.local`.

The local repository is defined in a mandatory section `[repository]`. This local repository can a bunch of plain files, a local git repo or even an tar archive.
The main option is `engine`, defining the kind of local repository. The complete list of the available kinds is here: :ref:`locals`.

You must define each source of this local repository in a `[source "name_of_the_source"]` section.
Again, you must set the `engine` option, defining the kind of source. Please check the list of available sources: :ref:`sources`.

You can also define some filters for transforming files (please check the :ref:`filters` section).

.. code-block::  ini
  :caption: /etc/polyarchiv/my-local.local

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

As said before, a remote repository is defined by a `ini` file in the configuration directory and with a name ending by `.remote`.
This config file requires a mandatory section `[repository]`.
The main option is `engine`, defining the kind of remote repository. Please check the list of available remote repositories: :ref:`remotes`.

By default, all remote repositories are used with all local repositories. Therefore, you should use at least the `name`
variable (the  name of the local repository) to backup several local repositories with the same remote repository.
Please check the section :ref:`variables` for a more detailed explanation.

URLs
----

Excepting git URLs, valid URLs must look like one of these examples:
  * `file:///foo/bar/baz` for direct file operation,
  * `ssh://username@hostname/boo/bar/baz`, but `keytab` or `private_key` must be set,
  * `http(s)://username:password@hostname/foo/bar/baz.git`, you can set `ca_cert` to the private root certificate or to `"any"` for accepting self-signed certificates.
  * `http(s)://:@hostname/foo/bar/baz.git` and `private_key` for certificate auth

Of course, `http`-like URLs require a WebDAV-compliant server (you can use Apache or Nginx).

URLs for git remotes must look like:
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

Most parameters for remote repositories can rely on time-based, or host-based, variables: for example,
`remote_url = ssh://example.org/backups/{hostname}/{name}-{Y}-{m}.tar.gz`.
If you restore your data on a brand new machine, there is no way to determine the previous `hostname`, nor
the time of the last backup (the `Y` and `m` values).
So, if your remote parameters depend on such variables, you should use the `metadata_url` parameter, allowing to
store (and retrieve!) these data to a predictible location.
This URL should either depend on the `name` variable or ends by `/` (allowing to append `{name}.json`).

Associating local and remote repositories
-----------------------------------------

All remote repositories apply to all local repositories but you can change this behaviour by applying tags to repositories.
By default, a local repository has the tag `local` and include all existing remote repositories: `included_remote_tags=*`.
A remote repository has the tag `remote` and include all local repositories: `included_local_tags=*`.

If large local repositories should not be sent to a given remote repository, you can exclude the "large" tags from the remote configuration:

.. code-block::  ini
  :caption: /etc/polyarchiv/my-remote.remote
  :name: tags1:/etc/polyarchiv/my-remote.remote

  [repository]
  engine=git
  excluded_local_tags=*large,huge

and add the `large` tag to the local configuration you want to avoid
(traditionnal shell expansion with ? and * is used for comparing included and excluded tags, so you can put `extra-large`
instead of simply `large`):

.. code-block:: ini
  :caption: /etc/polyarchiv/my-local.local
  :name: tags1:/etc/polyarchiv/my-local.local

  [repository]
  engine=git
  local_path=/tmp/local
  local_tags=local,extra-large


Tags can also be applied to remote repositories:

.. code-block:: ini
  :caption: /etc/polyarchiv/my-remote.remote
  :name: tags:/etc/polyarchiv/my-remote.remote

  [repository]
  engine=git
  remote_tags=small-only

and add the "large" tag to the local configuration:

.. code-block::  ini
  :caption: /etc/polyarchiv/my-local.local
  :name: tags:/etc/polyarchiv/my-local.local

  [repository]
  engine=git
  local_path=/tmp/local
  included_remote_tags=huge,large

Since the remote repository does not present either the `huge` tag or the `large` tag, it will not be applied.
