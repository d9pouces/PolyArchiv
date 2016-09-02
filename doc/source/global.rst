Global configuration
====================

Most of sources or backup/collect points require the presence of standard UNIX executables.
You can change their respective path in the global configuration.

Global configuration files are `.ini` files suffixed by `.global` that contains a `[global]` section. You can put as many global config files as you want in the config directory.


.. code-block:: ini
  :caption: /etc/polyarchiv/extra.global

  [global]
  rsync_executable=/opt/bin/rsync


.. polyengines:: config