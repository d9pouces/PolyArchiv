.. _variables:

Variables and replacement rules
===============================

Some repository parameters can be modified at runtime using custom variables.
Check `polyarchiv plugins -v` for a complete documentation of each customizable parameter.
By default, only the following variables are defined:

  * `name`: basename of the corresponding config collect point.
  * `fqdn`: local hostname, with the domain name (e.g., `vm1.test.example.org`)
  * `hostname`: local hostname (e.g., `vm1`)
  * the time of backup is also available, with a separate variable for each component: `Y`, `d` `M`, …
    Please check the `doc <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior>`_ to discover all of them.


.. warning::

  If you use time-dependent variables (or `hostname`, or `fqdn`), you should also use the `metadata_url` parameter.
  Check :ref:`remote_metadata` for more info.


In the local config file, you can add a new section `[variables]`.
Of course, the name of the option is the name of the variable.

In the remote config, you can also override some variables defined in collect points,
by adding a new section, specific to this collect point.
Check the example below, made of two collect points and a single remote one:

.. code-block:: ini
  :caption: /etc/polyarchiv/my-collect-point-1.collect
  :name: variables:/etc/polyarchiv/my-collect-point-1.collect

  [repository]
  engine=git
  [variables]
  group=MyGroup1

.. code-block:: ini
  :caption: /etc/polyarchiv/my-collect-point-2.collect
  :name: variables:/etc/polyarchiv/my-collect-point-2.collect

  [repository]
  engine=archive
  archive_name={name}-{Y}-{m}-{d}.tar.gz  <-- this is a customizable parameter
  [variables]
  group=MyGroup2
  name=my-collect-point-2
  ; you can override the default `name` variable

.. code-block:: ini
  :caption: /etc/polyarchiv/my-remote.remote
  :name: variables:/etc/polyarchiv/my-remote.remote

  [repository]
  engine=git
  remote_url=http://{host}/{group}/{name}.git  <-- another one
  ; requires a `group` variable in each collect point
  ; the `name` variable always exists
  [variables]
  host=gitlab.example.org

  [variables "my-collect-point-2"]
  group=MY-GROUP-2
  ; you can override the `group` variable of `my-collect-point-2` only in the `my-remote` remote repository.


With this configuration, `my-collect-point-1` is sent to `remote_url=http://gitlab.example.org/MyGroup1/my-collect-point-1.git` and
`my-collect-point-2` is sent to `remote_url=http://gitlab.example.org/MY-GROUP-2/my-collect-point-2.git`.
