NagiBack
========

Backup multiple data sources into git repositories and send them to remote repositories.

NagiBack manages multiple git repositories, each of them can store different kind of data.
You can specify several remotes, each of them handling one or more local repositories.

Each remote and each local repository has its own configuration file for configuring them independantly.

Local repositories
------------------

The configuration file of the local repository `myapp` is `/etc/nagiback/myapp.local`.
It is a `.ini` file with a section `[global]` and a section for each data source.



Remote repositories
-------------------

The configuration file of the local repository `myapp` is `/etc/nagiback/myremote.remote`.
It is a `.ini` file with a section `[global]` and a section per data source.

