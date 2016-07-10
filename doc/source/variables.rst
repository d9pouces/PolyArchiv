.. _variables:

Variables and replacement rules
===============================

Some repository parameters can be modified at runtime using custom variables.
Check `polyarchiv plugins -v` for a complete documentation of each customizable parameter.
By default, only the following variables are defined:

  * `name`: basename of the corresponding config local repository.
  * `fqdn`: local hostname, with the domain name (e.g., `vm1.test.example.org`)
  * `hostname`: local hostname (e.g., `vm1`)
  * the time of backup is also available, with a separate variable for each component: `Y`, `d` `M`, …
    Please check the `doc <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior>`_ to discover all of them.

In the local config file, you can add a new section `[variables]`.
Of course, the name of the option is the name of the variable.

In the remote config, you can also override some variables defined in local repositories,
by adding a new section, specific to this local repository.
Check the example below, made of two local repositories and a single remote one:

.. code-block:: bash

  cat /etc/polyarchiv/my-local-1.local
  [repository]
  engine=git
  [variables]
  group=MyGroup1

  cat /etc/polyarchiv/my-local-2.local
  [repository]
  engine=archive
  archive_name={name}-{Y}-{m}-{d}.tar.gz  <-- this is a customizable parameter
  [variables]
  group=MyGroup2
  name=MY-LOCAL-2
  ; you can override the default `name` variable

  cat /etc/polyarchiv/my-remote.remote
  [repository]
  engine=git
  remote_url=http://{host}/{group}/{name}.git  <-- another one
  ; requires a `group` variable in each local repository
  ; the `name` variable always exists
  [variables]
  host=gitlab.example.org

  [variables "my-local-2"]
  group=MY-GROUP-2
  ; you can override the `group` variable of `my-local-2` only in the `my-remote` remote repository.



With this configuration, `my-local-1` is sent to `remote_url=http://gitlab.example.org/MyGroup1/my-local-1.git` and
`my-local-2` is sent to `remote_url=http://gitlab.example.org/MY-GROUP-2/MY-LOCAL-2.git`.
