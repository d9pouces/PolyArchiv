.. _simple_project:

Simple web project
==================

A lot of web projects only have two kinds of data to backup:

  * a MySQL or PostgreSQL database,
  * a set of files uploaded by users.

Other kind of data (cached data, temp files, and of course the code) do not have to be backuped.
We only use a simple daily backup pattern: files copy and sql dump sent to a remote SSH server (say, backup.intranet.org).
Data are sent as a new archive every day, keeping the 7 last days, and at least one archive per week during 10 weeks (and then at least one archive per year).

Thus, we need to define a single collect point and a single backup points.

.. code-block:: bash

  mkdir -p /var/backups/www.example.com
  cat << EOF | sudo tee /etc/polyarchiv/www.example.com.collect
  [point]
  engine=files
  frequency=daily
  local_path=/var/backups/www.example.com
  collect_point_tags=website

  [source "database"]
  engine=postgressql
  host=localhost
  user=test
  password=p@ssw0rd
  database=testdb
  destination_path=./database.sql

  [source "files"]
  engine=local_files
  source_path=/var/www-data/files
  destination_path=files
  EOF


.. code-block:: bash

  cat << EOF | sudo tee /etc/polyarchiv/ssh.backup
  [point]
  engine=rolling_archive
  frequency=daily
  included_collect_point_tags=website
  daily_count=7
  weekly_count=10
  yearly_count=10
  remote_url=ssh://backupuser@backup.intranet.org:22/var/backups/{name}/backup-{Y}-{m}-{d}_{H}-{M}.tar.gz
  private_key=/home/backupuser/.ssh/id_rsa
  metadata_url=ssh://backupuser@backup.intranet.org:22/var/backups/{name}/metadata.json
  metadata_private_key=/home/backupuser/.ssh/id_rsa
  EOF

