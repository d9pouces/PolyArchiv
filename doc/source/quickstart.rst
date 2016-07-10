Quick start guide
=================

First, you obviously need to install Polyarchiv, and display the default configuration directory (should be `/etc/polyarchiv`):

.. code-block:: bash

  sudo pip install polyarchiv
  polyarchiv config

Then you can add a local repository, indicating the data to backup:

.. code-block:: bash

  mkdir -p /var/backups/my-project
  cat << EOF | sudo tee /etc/polyarchiv/my-project.local
  [repository]
  frequency=daily
  engine=files
  local_path=/var/backups/my-project
  frequency=daily

  [source "database"]
  engine=postgressql
  host=localhost
  user=test
  password=testtest
  database=testdb
  destination_path=./database.sql

  [source "files"]
  engine=rsync
  source_path=/var/my-project/data
  destination_path=./files
  EOF


And then we want to synchronize these data to a remote server using `rsync`.

.. code-block:: bash

  cat << EOF | sudo tee /etc/polyarchiv/my-server.remote
  [repository]
  engine=synchronize
  remote_url=ssh://backupuser@my-server/var/backups/remotes/{name}/
  private_key=/home/backupuser/.ssh/id_rsa
  EOF

You can now check your configuration, and execute the first backup step-by-step:

.. code-block:: bash

  polyarchiv config -v
  polyarchiv backup --show-commands --confirm-commands
