Cluster Job
===========

A cluster job is a zip file that MUST include the following files::

    jobname
    |- start_job
    |- meta.json
    `- submit_form.html

Metadata
--------

``meta.json`` MUST contain the following data and MAY contain more::

    {
        "name": "jobname",
        "description": "nothing to see here, move along",
        "version": "0.1",
    }

Executable
----------

``start_job`` MUST be executable, and takes the arguments

``--db``
    A valid zeromq url

``start_job`` SHOULD exit after a short time (< 1s). It starts a new process
that will be used for the actual computation and waits for this process to
connect to the database through zeromq. It MUST print the cluser job id it
recives, and no other information to stdout. (For the zeromq protocol see
below). If successfull it MUST return 0, and an error code otherwise. It SHOULD
use a secure zeromq connection.

``start_job`` MAY use drmaa to start new worker processes on the cluster. It
SOULD NOT use any other method (like qsub).

If the main process started by ``start_job`` gets a SIGTERM it SHOULD shut down
all worker processes and exit.

zeromq protocol
---------------


