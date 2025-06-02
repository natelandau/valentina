#!/usr/bin/env python

"""install_certifi.py.

Sample script to install or update a set of default Root Certificates
for the ssl module.  Uses the certificates provided by the certifi package:
https://pypi.python.org/pypi/certifi

Taken from: https://gist.github.com/marschhuynh/31c9375fc34a3e20c2d3b9eb8131d8f3

"""

import contextlib
import os
import os.path
import ssl
import stat
import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()

STAT_0o775 = (
    stat.S_IRUSR
    | stat.S_IWUSR
    | stat.S_IXUSR
    | stat.S_IRGRP
    | stat.S_IWGRP
    | stat.S_IXGRP
    | stat.S_IROTH
    | stat.S_IXOTH
)


def main() -> None:
    """Install or update a set of default Root Certificates for the ssl module."""
    openssl_dir, openssl_cafile = os.path.split(ssl.get_default_verify_paths().openssl_cafile)

    console.log("pip install --upgrade certifi")
    subprocess.check_call(  # noqa: S603
        [sys.executable, "-E", "-s", "-m", "pip", "install", "--upgrade", "certifi"],
    )

    import certifi

    # change working directory to the default SSL directory
    os.chdir(openssl_dir)
    relpath_to_certifi_cafile = os.path.relpath(certifi.where())
    console.log("removing any existing file or link")
    with contextlib.suppress(FileNotFoundError):
        Path(openssl_cafile).unlink()
    console.log("creating symlink to certifi certificate bundle")
    os.symlink(relpath_to_certifi_cafile, openssl_cafile)
    console.log("setting permissions")
    os.chmod(openssl_cafile, STAT_0o775)  # noqa: PTH101
    console.log("update complete")


if __name__ == "__main__":
    main()
