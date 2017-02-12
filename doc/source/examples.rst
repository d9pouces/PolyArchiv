Configuration examples
======================

First, you need to define one or more local collect points.

.. code-block:: ini
   :linenos:
   :name: local-backup.collect

    engine=files
    frequency=daily
    included_backup_point_tags=*
    local_path=/var/backups/local

.. code-block:: ini
   :linenos:
   :name: local-git-backup.collect

    engine=git
    frequency=daily
    included_backup_point_tags=*
    local_path=/var/backups/local.git

.. code-block:: ini
   :linenos:
   :name: svn-backup.collect

    engine=subversion
    included_backup_point_tags=
    excluded_backup_point_tags=*
    local_path=/var/backups/local.svn
    remote_url=file:///var/svn-repos/backups/{name}

