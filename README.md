PolyArchiv
==========


Backup data from multiple local sources (organized in local repositories) and send them to one or more remote repositories.

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
                                    
Configuration is based on standard `.ini` files, each file corresponding to one repository: 
    
  * `my-local-repo.local` defines a local repository named `my-local-repo`,
  * `my-remote-repo.remote` defines a remote repository named `my-remote-repo`.

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
  * smart_archive: creates an archive, pushes it to a remote location. Deletes some previous archives 
    (say, one per day during six days, then one per week during three weeks, then one per month during 12 months) 

These remote repositories are optional and you can of course use only local backups. All parameters (especially the remote location) can depend on the date and time, and on the hostname.

Each repository (either local or remote) is associated to a backup frequency. 
If a given repository has a daily backup frequency but you execute Polyarchiv twice a day, only the first backup will be executed.

Finally, all remote repositories must store some metadata at a predictable (independant of the time and hostname) remote location (HTTP/SSH/file).
These metadata can be required for restore operations.

Installation
------------

PolyArchiv uses Python, with no extra dependency.
The simplest way is to use `pip`, if it is installed on your system:

    $ pip install polyarchiv
    
You can also install it from the source:

    $ git clone https://github.com/d9pouces/PolyArchiv.git
    $ cd PolyArchiv
    $ python setup.py install 
    
    
Finally, you can use PolyArchiv without installation:

    $ git clone https://github.com/d9pouces/PolyArchiv.git
    $ cd PolyArchiv
    $ python run.py 

PolyArchiv is compatible with Python 2.7+ and Python 3.3+.

Several commands are available:
 
#### available engines

Display all available engines, for remote or local repositories, filters and sources (and their options if you specified `--verbose`)

    $ polyarchiv plugins [--verbose]

#### displaying configuration

Display the current configuration, local and remote repositories, sources and backup status

    $ polyarchiv config [-C /my/config/dir] [--verbose]

#### backup
 
Backup all data sources. If you set a frequency, repositories that are not out-of-date are not run (unless you specified `--force`)

    $ polyarchiv backup [-C /my/config/dir] [--force]
    
#### restore 

Restore the last version of your local repository

    $ polyarchiv restore [-C /my/config/dir] [--force]

#### build packages 

    $ ./debianize.sh  # create .deb package
    $ python setup.py bdist_rpm  # create .rpm package
    
#### other options

  * `-h`: show helps and exit
  * `-v`: verbose mode
  * `-f`: force backup operation, even if the most recent backup is still valid
  * `-n`: display a NRPE-compatible output
  * `-D`: no write action is performed
  * `--show-commands`: display all write actions as a bash operation
  * `--confirm-commands`: require a validation of each action
  * `--config`: specify another config dir
  * `--only-locals`: limit operations to the local repositories with this tags (can be used several times)
  * `--only-remotes`: limit operations to the remote repositories with this tags (can be used several times)
    
Next steps
----------

  * run `polyarchiv plugins -v` to check available sources and repositories
  * create config files for your local repositories (you should organize all your backups in several local repository, maybe one per service)
  * create config files for your remote servers (one config file per server)
  * run `polyarchiv config -v` to check your configuration
  * run `polyarchiv backup --dry --show-commands --force` to check the executed script
  * run `polyarchiv backup` in a cron :-)
    
Configuration
-------------

The default configuration directory is `/etc/polyarchiv` unless you installed it in a virtualenv, 
(then its default config dir is `$VIRTUALENV/etc/polyarchiv`). 
Otherwise, you can specify another config dir with `polyarchiv -C /my/config/dir`.

This directory should contain configuration files for local repositories 
(like `my-local.local`) as well as remote repositories (like `my-remote.remote`).

Here is an example of local repository, gathering data from three sources:

  * PostgresSQL database
  * MySQL database
  * a directory

Its name must end by `.local`. 
The `[repository]` section defines options for the local repository (the engine that powers the local backup, the frequency, …), and other sections define the three sources:

    $ cat /etc/polyarchiv/my-local.local
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

The kind of repository (either local or remote) and of each source is defined by the `engine` option.
You can define as many local repositories (each of them with one or more sources) as you want.

Remote repositories are simpler and by default only have a `[repository]` section.
Their names must end by `.remote`.
Here is a gitlab acting as remote storage for git local repo: 

    $ cat /etc/polyarchiv/my-remote1.remote
    [repository]
    engine=git
    frequency=daily
    remote_tags=
    remote_url=http://gitlab.example.org/group/%(name)s.git
    remote_branch=master
    user=mgallet
    included_local_tags=*

`%(name)s` will be replaced by the name of the local repository; for example the name of the `my-local.local` local repository is 
obviously `my-local`). You can specify (a bit) more complex replacement rules (see below).

Maybe you also want a full backup (as an archive) uploaded monthly (the tenth day of each month) to a FTP server:

    $ cat /etc/polyarchiv/my-remote2.remote
    [repository]
    engine=tar
    frequency=monthly:10
    remote_tags=
    remote_url=ftp://myftp.example.org/backups/%(name)s/
    remote_branch=master
    user=mgallet
    password=p@ssw0rd
    tar_format=tar.xz
    included_local_tags=*

Configuration files can be owned by different users: files that are unreadable by the current user are ignored.

Available engines
-----------------

Several engines for sources and remote or local repositories are available.
Use `polyarchiv plugins` to display the full list, and `polyarchiv plugins -v` to display all their configuration options.
 
Extra backup options
--------------------

  * `--verbose`: display more info
  * `--force`: force the backup, even if not required (the last backup is recent enough)
  * `--nrpe`: the output is compatible with Nagios/NRPE (so you can use it as a standard Nagios check in your sup)
  * `--show-commands`: display all operations as a plain Bash script
  * `--confirm-commands`: display all operations and ask for a manual confirmation before running them
  * `--dry`: does not actually perform operations
  * `--only-locals`: limit used local repositories to these tags
  * `--only-remotes`: limit used remote repositories to these tags

Associating local and remote repositories
-----------------------------------------

All remote repositories apply to all local repositories but you can change this behaviour by applying tags to repositories.
By default, a local repository has the tag `local` and include all remote repositories `included_remote_tags=*`.
A remote repository has the tag `remote` and include all local repositories `included_local_tags=*`.

If large local repositories should not be sent to a given remote repository, you can exclude the "large" tags from the remote configuration:
 
    $ cat /etc/polyarchiv/my-remote.remote
    [repository]
    engine=git
    excluded_local_tags=*large,huge

and add the "large" tag in the local configuration:

    $ cat /etc/polyarchiv/my-local.local
    [repository]
    engine=git
    local_path=/tmp/local
    local_tags=local,large

Traditionnal shell expansion is used for comparing included and excluded tags. Tags can be applied to remote repositories:

    $ cat /etc/polyarchiv/my-remote.remote
    [repository]
    engine=git
    remote_tags=small-only

and add the "large" tag to the local configuration:

    $ cat /etc/polyarchiv/my-local.local
    [repository]
    engine=git
    local_path=/tmp/local
    included_remote_tags=huge,large
    
Since the remote repository does not present either the `huge` tag or the `large` tag, it will not be applied.

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
  * `http(s)://username:password@hostname/foo/bar/baz.git`
  * `http(s)://:@hostname/foo/bar/baz.git` (but `keytab` must be set, not the `:@` in the URL!)
  

Replacement rules
-----------------

Some repository parameters can be modified at runtime using custom variables.
Check `polyarchiv plugins -v` for a complete documentation of each customizable parameter.
By default, only the following variables are defined:

  * `name`: basename of the corresponding config local repository.
  * `fqdn`: local hostname, with the domain name (e.g., `vm1.test.example.org`)
  * `hostname`: local hostname (e.g., `vm1`)
  * the time of backup is also available, with a separate variable for each component: `Y`, `d` `M`, …
    Please check https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior to discover all of them.

In the local config file, you can add a new section `[variables]`. 
Of course, the name of the option is the name of the variable.

In the remote config, you can also override some variables defined in local repositories,
by adding a new section, specific to this local repository.
Check the example below:

    $ cat /etc/polyarchiv/my-local-1.local
    [repository]
    engine=git
    [variables]
    group=MyGroup1
    
    $ cat /etc/polyarchiv/my-local-2.local
    [repository]
    engine=archive
    archive_name=%(name)s-%(Y)s-%(m)-%(d)s.tar.gz  <-- this is a customizable parameter
    [variables]
    group=MyGroup2
    name=MY-LOCAL-2
    ; you can override the default `name` variable

    $ cat /etc/polyarchiv/my-remote.remote
    [repository]
    engine=git
    remote_url=http://%(host)s/%(group)s/%(name)s.git  <-- another one
    ; requires a `group` variable in each local repository
    ; the `name` variable always exists
    [variables]
    host=gitlab.example.org
    
    [variables "my-local-2"]
    group=MY-GROUP-2
    ; you can override the `group` variable of `my-local-2` only in the `my-remote` remote repository.

`my-local-1` is sent to `remote_url=http://gitlab.example.org/MyGroup1/my-local-1.git`.
`my-local-2` is sent to `remote_url=http://gitlab.example.org/MY-GROUP-2/MY-LOCAL-2.git`.

File filters
------------

Currently, a local repository gather some files from its sources and expose them to all remote repositories.
You can add some treatment on these files, before sending them to the remote repositories.
These operation can happen after the local backup, or only before a given remote backup.
Imagine you want to encrypt your backup files, and you have two remote and two local repositories.

### First case

You must apply the encryption filter to all local repositories you wan to protect. 
Original data are still available on the disk but not used by remote repositories. 

### Second case

All local repositories that are processed by the remote repositories are encrypted.
However, if you use several remote repositories, the encryption process is performed several times.
Moreover, clear-text data are still available on the disk.

### Applying filters

You only have to add a `[filter "my filter name"]` section to your config file. 
Of course, you can use several filters, there are applied in the order of apparition in the config file.

    $ cat /etc/polyarchiv/my-local-1.local
    [repository]
    engine=git
    [filter "hash"]
    engine=hashes
    method=sha1
    [filter "encrypt"]
    password=p@ssw0rd
    engine=encrypt
    
Remote metadata storage
-----------------------

Most parameters for remote repositories can rely on time-based, or host-based, variables.
For example, `remote_url = ssh://example.org/backups/%(hostname)s/%(name)s-%(Y)s-%(m)s.tar.gz`.
If you restore your data on a brand new machine, there is no way to determine the previous `hostname`, nor
the time of the last backup (the `Y` and `m` values).
So, when your remote parameters depends on such variables, you should use a metadata_url 

Adding your engines
-------------------

PolyArchiv is designed to be extensible. You can add your own engines for all kinds of engines:

  * remote repositories (must inherit from `polyarchiv.remotes.RemoteRepository`),
  * local repositories (must inherit from `polyarchiv.locals.LocalRepository`),
  * filters (must inherit from `polyarchiv.sources.Source`),
  * sources (must inherit from `polyarchiv.filters.FileFilter`).
  
To use them, they must be installed in the current PYTHONPATH.
You can either directly use the dotted path in the configuration files:

    $ cat /etc/polyarchiv/my-local.local
    [repository]
    engine=mypackage.myengines.MyLocalRepository
    local_path=/tmp/local

    [source "source_1"]
    engine=mypackage.myengines.MySource

You can also register them as new setuptools entry points:

  * `polyarchiv.sources`,
  * `polyarchiv.remotes`,
  * `polyarchiv.locals`,
  * `polyarchiv.filters`. 

The key is the alias used in config files, the value is the dotted path.