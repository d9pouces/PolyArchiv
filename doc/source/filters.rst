.. _filters:

Filters
=======

By default, a collect point gather some files from its sources and expose them to all backup points.
You can apply some changes on these files, before sending them to the backup points.
These operation can happen after the collect, or only before a given remote backup.
Imagine you want to encrypt your backup files, and you have two backup points and two collect points.

.. code-block:: bash

                               collect point                                                   backup point 1
  /------------------------------------------------------------------------\        /-----------------------------------------------\
  | /------------------\     /----------\     /----------\     /---------\ |        | /----------\     /----------\     /---------\ |
  | | source 1: files  | --> |          | --> |          | --> |         | |        | |          | --> |          | --> |         | |
  | \------------------/     |          |     |          |     | collect | |        | |          |     |          |     | backup  | |
  |                          | filter 1 |     | filter 2 |     | storage | | ---+-> | | filter 3 |     | filter 4 |     | storage | |
  | /------------------\     |          |     |          |     |         | |    |   | |          |     |          |     |         | |
  | | source 2: MySQL  | --> |          | --> |          | --> |         | |    |   | |          | --> |          | --> |         | |
  | \------------------/     \----------/     \----------/     \---------/ |    |   | \----------/     \----------/     \---------/ |
  \------------------------------------------------------------------------/    |   \-----------------------------------------------/
                                                                                |
                                                                                |
                                                                                v   backup point 2
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

Example: you must apply the encryption filter to all collect points you wan to protect.
Original (not crypted!) data are still available on the disk but not used by backup points.

Second case
-----------

Example: all collect points that are processed by the backup points are encrypted.
However, if you use several backup points, the encryption process is performed several times.
Moreover, clear-text data are still available on the disk.

Applying filters
----------------

You only have to add a `[filter "name_of_the_filter"]` section to your config file.
Of course, you can use several filters, there are applied in the order of apparition in the config file.

.. code-block:: ini
  :caption: /etc/polyarchiv/my-collect-point-1.collect

  [point]
  engine=git
  [filter "hash"]
  engine=hashes
  method=sha1
  [filter "encrypt"]
  password=p@ssw0rd
  engine=encrypt

Built-in filters
----------------

Required parameters are marked in red.

.. polyengines:: filters