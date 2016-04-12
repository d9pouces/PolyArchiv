NagiBack
========

Backup data from multiple local sources (organized in local repositories) and send them to one or more remote repositories.
Configuration is based on simple files: 
    
  * `my-local-repo.local` defines a local repository named "my-local-repo",
  * `my-remote-repo.remote` defines a remote repository named "my-remote-repo".
  
Each local repository defines one or more data sources (all of them are defined in the my-local-repo.local file:

  * directory with files,
  * MySQL or PostgreSQL database to dump,
  * OpenLDAP database to dump.

There are several kinds of local repositories:

  * raw files,
  * local git repository: after each backup, files that have been gathered from the different sources are added and locally commited.
  
There are also several kinds of remote repositories:

  * GitRepository (requires a local git repository): after the backup, local commits are pushed to this remote git repository,
  * Rsync: after the backup, all files are synchronized to the remote repository,
  * TarArchive: after the backup, all files are archived in a single .tar.gz archive and sent to the remote repo (via ftp, scp, http, smb, or a basic cp)

Each repository (either local or remote) is associated to a frequency of backup. 
If you specify a daily backup for a given repository and you execute Nagiback twice a day, only the first backup will be executed. 

Installation
------------

The simplest way is to use `pip`:

    $ pip install nagiback

Some commands are available:
display the current configuration, local and remote repositories, sources and backup status

    $ nagiback show [-C /my/config/dir] [--verbose]

backup data. If you set a frequency, repositories that are not out-of-date are not run (unless you specified `--force`)

    $ nagiback backup [-C /my/config/dir] [--force]
 
display all available engines (and their options if you specified `--verbose`)

    $ nagiback help [--verbose]

You can also generate a Debian/Ubuntu package with: 

    sudo apt-get install python-stdeb
    python setup.py --command-packages=stdeb.command  bdist_deb

Configuration
-------------

The default configuration directory is /etc/nagiback. However, if you installed it in a virtualenv, 
then its default config dir is `$VIRTUALENV/etc/nagiback`. 
Otherwise, you can specify another config dir with `nagiback -C /my/config/dir`.

This directory contains configuration files for local repositories 
(like `my-local.local`) as well as remote repositories (like `my-remote.remote`).

Here is an example of local repository, gathering data from three sources:

  * PostgresSQL database
  * MySQL database
  * a directory

The `[global]` section defines options for the local repository, and other sections define the three sources:

    $ cat /etc/nagiback/my-local.local
    [global]
    engine=nagiback.locals.GitRepository
    local_path=/tmp/local
    local_tags=local
    included_remote_tags=*
    excluded_remote_tags=
    frequency=daily
    
    [source_1]
    engine=nagiback.sources.PostgresSQL
    host=localhost
    port=5432
    user=test
    password=testtest
    database=testdb
    destination_path=./postgres.sql
    
    [source_2]
    engine=nagiback.sources.MySQL
    host=localhost
    port=3306
    user=test
    password=testtest
    database=testdb
    destination_path=./mysql.sql
    
    [source_3]
    engine=nagiback.sources.RSync
    source_path=/tmp/source/files
    destination_path=./files

The kind of repository (either local or remote) and of each source is defined by the "engine" option.
You can define as many local repositories (each of them with one or more sources) as you want.
Remote repositories are simpler and only have a `[global]` section. Here is a gitlab acting as remote storage for git local repo: 

    $ cat /etc/nagiback/my-remote1.remote
    [global]
    engine=nagiback.remotes.GitRepository
    frequency=daily
    remote_tags=
    remote_url=http://gitlab.example.org/group/TestsNagiback.git
    remote_branch=master
    user=mgallet
    included_local_tags=*

Maybe you also want a full backup (as an archive) uploaded monthly (the tenth day of each month) to a FTP server:

    $ cat /etc/nagiback/my-remote2.remote
    [global]
    engine=nagiback.remotes.TarArchive
    frequency=monthly:10
    remote_tags=
    remote_url=ftp://myftp.example.org/backups/project/
    remote_branch=master
    user=mgallet
    password=p@ssw0rd
    tar_format=tar.xz
    included_local_tags=*

Configuration files can be owned by different users: files that are unreadable by the current user are ignored.

Available engines
-----------------

Several engines for sources and remote or local repositories are available.
Use `nagiback help` to display them (and `nagiback help -v` to display their configuration options). 

Associating local and remote repositories
-----------------------------------------

With no restriction, all remote repositories apply to all local repositories but you can change this behaviour by applying tags to repositories.
By default, a local repository has the tag `local` and include all remote repositories `included_remote_tags=*`.
A remote repository has the tag `remote` and include all local repositories `included_local_tags=*`.

If large local repositories should not be sent to a given remote repository, you can exclude the "large" tags in the remote configuration:
 
    $ cat /etc/nagiback/my-remote.remote
    [global]
    engine=nagiback.remotes.GitRepository
    excluded_local_tags=large

and add the "large" tag in the local configuration:

    $ cat /etc/nagiback/my-local.local
    [global]
    engine=nagiback.locals.GitRepository
    local_path=/tmp/local
    local_tags=local,large
