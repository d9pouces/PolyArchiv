NagiBack
========

Backup data from multiple local sources (organized in local repositories) and send them to one or more remote repositories.
Configuration is based on simple files: 
    
  * my-local-repo.local define a local repository named "my-local-repo",
  * my-remote-repo.remote define a remote repository named "my-remote-repo".
  
Each local repository defines one or more data sources (all of them are defined in the my-local-repo.local file:

  * directory with files,
  * MySQL or PostgreSQL database to dump,
  * OpenLDAP database to dump.

There are several kinds of local repositories:

  * raw files,
  * local git repository: after each backup, files that have been gathered from the different sources are added and commited.
  
There are also several kinds of remote repositories:

  * GitRepository (requires a local git repository): after the backup, local commits are pushed to this remote git repository,
  * Rsync: after the backup, all files are synchronized to the remote repository,
  * TarArchive: after the backup, all files are archived in a single .tar.gz archive and sent to the remote repo (via ftp, scp, http, smb, or a basic cp)

Each repository (either local or remote) is associated to a frequency of backup. 
If you specify a daily backup for a given repository and you execute Nagiback twice a day, only the first backup will be executed. 

Installation
------------

The simplest way is to use `pip`:

    pip install nagiback
    

Configuration
-------------

The default configuration directory is /etc/nagiback. However, if you installed it in a virtualenv, 
then its default config dir is $VIRTUALENV/etc/nagiback. 
Otherwise, you can specify another config dir with `nagiback -C /my/config/dir`.

The selected configuration directory should contain configuration files for local repositories (like `my-local.local`).

Backup data
-----------
