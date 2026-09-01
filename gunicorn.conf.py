"""Production Gunicorn settings for the read-only container runtime.

Gunicorn 25.1+ enables its control socket by default.  Keep all Gunicorn
runtime state on the container's ephemeral tmpfs rather than the immutable
application filesystem.  The socket remains private to the sentinel user.
"""

# The staging Compose profile mounts /tmp as tmpfs.  This path is also valid
# for the image's non-staging runtimes, where /tmp remains container-local.
control_socket = "/tmp/sentinel-dna-gunicorn.ctl"
control_socket_mode = 0o600
worker_tmp_dir = "/tmp"
