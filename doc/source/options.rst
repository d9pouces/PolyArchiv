.. _options:

Running options
===============

The `polyarchiv` command requires exactly one argument, that can be:

  * `config`: display the current configuration and loaded configuration files,
  * `backup`: backup all required data,
  * `restore`: restore backuped data,
  * `plugins`: display all available plugins and their respective help.

There are some optional arguments, mainly for backup operations:

  * `-C`: change the configuration directory,
  * `-v` or `--verbose`: display more information (useful for backups or the `plugins`),
  * `-f` or `--force` (only for backups): force the backup, even if the last backup is recent enough (see the `frequency` option),
  * `-n` or `--nrpe` (only for backups): display a Nagios-like output (and the appropriate exit code),
  * `-D` or `--dry` (backup or restore): do not perform any write operation (can lead to errors if a read action requires a previous write),
  * `--show-commands` (backup or restore): display all actions as a Bash command,
  * `--confirm-commands` (backup or restore): ask the user to confirm each command
  * `--only-collect-points` (backup or restore): only apply to the collect points with these tags (can be used several times, and ? or * jokers are valid)
  * `--only-remotes` (backup or restore): only apply to the remote repositories with these tags (can be used several times, and ? or * jokers are valid)
  * `--skip-collect` (backup only): skip the collect step during a backup
  * `--skip-remote` (backup only): skip the remote step during a backup

