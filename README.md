PolyArchiv
==========

Backup data from multiple 'sources' (organized in 'collect points') and copy them to one or more 'backup points'.
The complete doc is available here: http://polyarchiv.readthedocs.io/en/latest/ 

       collect point 1: /var/backups/local1             /----------------------\
       data of www.github.com               ________\__ | backup point 1: git  |
    /------------------------\             /        /   |   data of local 1    |
    |     source 1: files    |---->-------/             \----------------------/
    |     source 2: mysql    |                          * http://mygit/backups/local1.git
    |     source 3: mysql    |---->-------\
    \------------------------/             \________\___ /--------------------------\
                                                    /    | backup point 2: tar+curl |
     collect point 2: : /var/backups/local2              |   data of local 1        | 
     data of www.example.com                ________\___ |   data of local 2        |
    /------------------------\             /        /    \--------------------------/
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
                                    
Configuration is based on standard `.ini` files, each file corresponding to one collect or backup point: 
    
  * `my-collect-point.collect` defines a collect point named `my-collect-point`,
  * `my-backup-point.backup` defines a backup point named `my-backup-point`.

Each collect point must define a base folder and one or more data sources, all of them being defined in the `my-collect-point.collect` file:

  * directory with files,
  * MySQL or PostgreSQL database to dump,
  * Dovecot mails,
  * OpenLDAP database to dump.

There are several kinds of collect points:

  * raw files,
  * local git repository: after each backup, files that have been gathered from the different sources are added and locally commited.
  * archive: all collected files are merged into a single .tar.(gz/bz2/xz) archive.
  
There are also several kinds of backup points:

  * git: the whole collect point is pushed to this remote git repository, 
  * gitlab: almost identical to the previous one, but able to automatically create the backup point,
  * synchronize: uses rsync to copy all files to a new, probably remote, location,
  * archive: creates an archive (.tar.gz/bz2/xz) and pushes it to a remote location, 
  * rolling_archive: creates an archive, pushes it to a remote location. Deletes some previous archives 
    (say, one per day during six days, then one per week during three weeks, then one per month during 12 months) 

These backup points are optional and you can of course use only local collect points, for example when your collect point is stored on a NFS share. All parameters (especially the remote location) can depend on the date and time, and on the hostname.

Each backup point (either collect ones or backup ones) is associated to a backup frequency. 
If a given point has a daily backup frequency but you execute Polyarchiv twice a day, only the first backup will be executed.

Installation
------------

PolyArchiv uses plain Python, with no extra dependency.
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

Display all available engines, for collect/backup points, filters and sources (and their options if you specified `--verbose`)

    $ polyarchiv plugins [--verbose]

#### displaying configuration

Display the current configuration, collect/backup points, sources and backup status

    $ polyarchiv config [-C /my/config/dir] [--verbose]

#### backup
 
Backup all data sources. If you set a frequency, collect and backup points that are not out-of-date are not run (unless you specified `--force`)

    $ polyarchiv backup [-C /my/config/dir] [--force]
    
#### restore 

First fetch data from the most recent backup point to the collect point, then restore each source. 

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
  * `--log-file`: log all output to this file
  * `--show-commands`: display all write actions as a bash operation
  * `--confirm-commands`: require a validation of each action
  * `--config`: specify another config dir
  * `--only-collect-points`: limit operations to the collect points corresponding to this tags (can be used several times)
  * `--only-backup-points`: limit operations to the backup points with this tags (can be used several times)
    
Next steps
----------

  * run `polyarchiv plugins -v` to check available kinds of sources and collect/backup points
  * create config files for your collect points (you should organize all your backups in several collect point, maybe one per service)
  * create config files for your remote servers (one config file per server)
  * run `polyarchiv config -v` to check your configuration
  * run `polyarchiv backup --dry --show-commands --force` to check the executed script
  * run `polyarchiv backup` in a cron :-)
    
Configuration
-------------

The default configuration directory is `/etc/polyarchiv` unless you installed it in a virtualenv, 
(then its default config dir is `$VIRTUALENV/etc/polyarchiv`). 
Otherwise, you can specify another config dir with `polyarchiv -C /my/config/dir`.

This directory should contain configuration files for collect points 
(like `my_collect_point.collect`) as well as backup points (like `my_backup_point.backup`).

Here is an example of collect point, gathering data from three sources:

  * PostgresSQL database
  * MySQL database
  * a directory

Its name must end by `.collect`. 
The `[point]` section defines options for the collect point (the engine that powers the local backup, the frequency, …), while other sections define the three sources:

    $ cat /etc/polyarchiv/my-collect-point.collect
    [point]
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

The kind of points (collect or backup) and of each source is defined by the `engine` option.
You can define as many collect points (each of them with one or more sources) as you want.

Backup points are simpler and by default only have a `[point]` section.
Their names must end by `.backup`.
Here is a gitlab acting as remote storage for git local repo: 

    $ cat /etc/polyarchiv/my-backup-point1.backup
    [point]
    engine=git
    frequency=daily
    backup_point_tags=
    remote_url=http://gitlab.example.org/group/{name}.git
    remote_branch=master
    user=mgallet
    included_collect_point_tags=*

`{name}` will be replaced by the name of the collect point; for example the name of the `my-collect-point.collect` collect point is 
obviously `my-collect-point`). You can use (a bit) more complex replacement rules (see the doc).

Maybe you also want a full backup (as an archive) uploaded the tenth day of each month, to a HTTP server:

    $ cat /etc/polyarchiv/my-backup-point2.backup
    [point]
    engine=archive
    frequency=monthly:10
    backup_point_tags=
    remote_url=http://user:p@ssw0rd@myserver.example.org/backups/{name}/
    tar_format=tar.xz
    included_collect_point_tags=*

Configuration files can be owned by different users: files that are unreadable by the current user are simply ignored.

Available engines
-----------------

Several engines for sources or collect/backup points are available.
Use `polyarchiv plugins` to display the full list, and `polyarchiv plugins -v` to display all their configuration options.
 
Extra backup options
--------------------

  * `--verbose`: display more info
  * `--force`: force the backup, even if not required (the last backup is recent enough)
  * `--nrpe`: the output is compatible with Nagios/NRPE (so you can use it as a standard Nagios check in your sup)
  * `--show-commands`: display all operations as a plain Bash script
  * `--confirm-commands`: display all operations and ask for a manual confirmation before running them
  * `--dry`: does not actually perform operations
  * `--only-collect-points` (backup or restore): only apply to the collect points with these tags (can be used several times, and ? or * jokers are valid)
  * `--only-backup-points` (backup or restore): only apply to the backup points with these tags (can be used several times, and ? or * jokers are valid)
  * `--skip-collect` (backup only): skip the collect step during a backup
  * `--skip-backup` (backup only): skip the backup step during a backup

Adding your engines
-------------------

PolyArchiv is designed to be extensible. You can add your own engines for all kinds of engines:

  * backup points (must inherit from `polyarchiv.backup_points.BackupPoint`),
  * collect points (must inherit from `polyarchiv.collect_points.CollectPoint`),
  * filters (must inherit from `polyarchiv.sources.Source`),
  * sources (must inherit from `polyarchiv.filters.FileFilter`).
  
To use them, they must be installed in the current PYTHONPATH.
You can either directly use the dotted path in the configuration files:

    $ cat /etc/polyarchiv/my-collect.collect
    [point]
    engine=mypackage.myengines.MyCollectPoint
    local_path=/tmp/local

    [source "source_1"]
    engine=mypackage.myengines.MySource

You can also register them as new setuptools entry points:

  * `polyarchiv.sources`,
  * `polyarchiv.backup_points`,
  * `polyarchiv.collect_points`,
  * `polyarchiv.filters`. 

The key is the alias used in config files, the value is the dotted path.