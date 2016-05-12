Polyarchiv
==========


Backup data from multiple local sources (organized in local repositories) and send them to one or more remote repositories.

                                                    /--------------------------\
       local repository 1: git          ________\__ | remote repository 1: git |
    /------------------------\         /        /   |   data of local 1        |
    |     source 1: files    |---->---/             \--------------------------/
    |     source 2: mysql    |                      
    |     source 3: mysql    |---->---\
    \------------------------/         \________\___ /----------------------------\
                                                /    | remote repository 2: files |
                                                     |   data of local 1          | 
     local repository 2: files          ________\___ |   data of local 2          |
    /------------------------\         /        /    \----------------------------/
    |     source 1: files    |---->---/
    |     source 2: mysql    |
    \------------------------/
    
    
Configuration is based on simple `.ini` files: 
    
  * `my-local-repo.local` defines a local repository named `my-local-repo`,
  * `my-remote-repo.remote` defines a remote repository named `my-remote-repo`.
  
Each local repository defines one or more data sources, all of them being defined in the `my-local-repo.local` file:

  * directory with files,
  * MySQL or PostgreSQL database to dump,
  * OpenLDAP database to dump.

There are several kinds of local repositories:

  * raw files,
  * local git repository: after each backup, files that have been gathered from the different sources are added and locally commited.
  
There are also several kinds of remote repositories:

  * gitrepository (requires a local git repository): after the backup, local commits are pushed to this remote git repository,
  * rsync: after the backup, all files are synchronized to the remote repository,
  * tararchive: after the backup, all files are archived in a single .tar.gz archive and sent to the remote repo (via ftp, scp, http, smb, or a basic cp),
  * duplicity: after the backup, all files are encrypted and sent to the remote repository.

Each repository (either local or remote) is associated to a backup frequency. 
If a given repository has a daily backup frequency but you execute Polyarchiv twice a day, only the first backup will be executed. 

Installation
------------

The simplest way is to use `pip`:

    $ pip install polyarchiv
    
You can also install it from the source:

    $ git clone https://github.com/d9pouces/PolyArchiv.git
    $ cd PolyArchiv
    $ python setup.py install 
    
If you do not want to globally install it, you can use the `--user` option.

Some commands are available:
display the current configuration, local and remote repositories, sources and backup status

    $ polyarchiv config [-C /my/config/dir] [--verbose]

backup data. If you set a frequency, repositories that are not out-of-date are not run (unless you specified `--force`)

    $ polyarchiv backup [-C /my/config/dir] [--force]
 
display all available engines (and their options if you specified `--verbose`)

    $ polyarchiv plugins [--verbose]

You can also generate a Debian/Ubuntu package with: 

    sudo apt-get install python-stdeb
    python setup.py --command-packages=stdeb.command  bdist_deb
    
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
    
    [source_1]
    engine=postgressql
    host=localhost
    port=5432
    user=test
    password=testtest
    database=testdb
    destination_path=./postgres.sql
    
    [source_2]
    engine=mysql
    host=localhost
    port=3306
    user=test
    password=testtest
    database=testdb
    destination_path=./mysql.sql
    
    [source_3]
    engine=rsync
    source_path=/tmp/source/files
    destination_path=./files

The kind of repository (either local or remote) and of each source is defined by the `engine` option.
You can define as many local repositories (each of them with one or more sources) as you want.
**You cannot use `DEFAULT`, `repository` or `variables` as source name.**

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

  * `--verbose`: display more infos
  * `--force`: force the backup, even if not required (the last backup is recent enough)
  * `--nrpe`: the output is compatible with Nagios/NRPE (so you can use it like a standard Nagios check in your sup)
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

Replacement rules
-----------------

Some parameters of remote repositories may use variables to be customized for each local repository.
Check `polyarchiv plugins -v` for a complete documentation of each parameter.
By default, only the `name` variable is defined and is equal to the basename of the corresponding config file.

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
    engine=git
    [variables]
    group=MyGroup2
    name=MY-LOCAL-2
    ; you can override the default `name` variable

    $ cat /etc/polyarchiv/my-remote.remote
    [repository]
    engine=git
    remote_url=http://gitlab.example.org/%(group)s/%(name)s.git
    ; requires a `group` variable in each local repository
    ; the `name` variable always exists
    
    [my-local-2]
    group=MY-GROUP-2
    ; you can override the `group` variable of `my-local-2` only in the `my-remote` remote repository.

`my-local-1` is sent to `remote_url=http://gitlab.example.org/MyGroup1/my-local-1.git`.
`my-local-2` is sent to `remote_url=http://gitlab.example.org/MY-GROUP-2/MY-LOCAL-2.git`.