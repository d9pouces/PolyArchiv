Filters
=======

By default, a local repository gather some files from its sources and expose them to all remote repositories.
You can apply some changes on these files, before sending them to the remote repositories.
These operation can happen after the local backup, or only before a given remote backup.
Imagine you want to encrypt your backup files, and you have two remote and two local repositories.

.. code-block:: bash

                               local repository                                                   remote repository 1
  /------------------------------------------------------------------------\        /-----------------------------------------------\
  | /------------------\     /----------\     /----------\     /---------\ |        | /----------\     /----------\     /---------\ |
  | | source 1: files  | --> |          | --> |          | --> |         | |        | |          | --> |          | --> |         | |
  | \------------------/     |          |     |          |     |  local  | |        | |          |     |          |     | remote  | |
  |                          | filter 1 |     | filter 2 |     | storage | | ---+-> | | filter 3 |     | filter 4 |     | storage | |
  | /------------------\     |          |     |          |     |         | |    |   | |          |     |          |     |         | |
  | | source 2: MySQL  | --> |          | --> |          | --> |         | |    |   | |          | --> |          | --> |         | |
  | \------------------/     \----------/     \----------/     \---------/ |    |   | \----------/     \----------/     \---------/ |
  \------------------------------------------------------------------------/    |   \-----------------------------------------------/
                                                                                |
                                                                                |
                                                                                v   remote repository 2
                                                                        /------------------------------\
                                                                        | /----------\     /---------\ |
                                                                        | |          | --> |         | |
                                                                        | |          |     | remote  | |
                                                                        | | filter 5 |     | storage | |
                                                                        | |          |     |         | |
                                                                        | |          | --> |         | |
                                                                        | \----------/     \---------/ |
                                                                        \------------------------------/

First case
----------

You must apply the encryption filter to all local repositories you wan to protect.
Original data are still available on the disk but not used by remote repositories.

Second case
-----------

All local repositories that are processed by the remote repositories are encrypted.
However, if you use several remote repositories, the encryption process is performed several times.
Moreover, clear-text data are still available on the disk.

Applying filters
----------------

You only have to add a `[filter "my filter name"]` section to your config file.
Of course, you can use several filters, there are applied in the order of apparition in the config file.

.. code-block:: bash

  cat /etc/polyarchiv/my-local-1.local
  [repository]
  engine=git
  [filter "hash"]
  engine=hashes
  method=sha1
  [filter "encrypt"]
  password=p@ssw0rd
  engine=encrypt

