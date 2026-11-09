# Local Spark configuration

The launcher sets SPARK_CONF_DIR to this directory for its child process only.
There is intentionally no spark-env.cmd or spark-defaults.conf. This avoids
inheriting global package resolution, remote cluster settings and Java options.
Job arguments and the Scala entry point supply the bounded localhost settings.
Do not add credentials, automatic downloads or unreviewed resolver defaults.
