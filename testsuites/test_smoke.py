"""Runs a 'smoke' test for an Azure Linux VM deployment."""
import logging
import socket

from invoke.runners import Result  # type: ignore
from paramiko import SSHException  # type: ignore

import pytest
from node_plugin import Node


@pytest.mark.deploy(setup="OneVM", vm_size="Standard_DS2_v2")
def test_smoke(urn: str, node: Node) -> None:
    """Check that a VM can be deployed and is responsive.

    1. Deploy the VM (via 'node' fixture) and log it.
    2. Ping the VM.
    3. Connect to the VM via SSH.
    4. Attempt to reboot via SSH, otherwise use the platform.
    5. Fetch the serial console logs.

    For commands where we expect a possible non-zero exit code, we
    pass 'warn=True' to prevent it from throwing 'UnexpectedExit' and
    we instead check its result at the end.

    SSH failures DO NOT fail this test.

    """
    logging.info("Pinging before reboot...")
    ping1: Result = node.ping(warn=True)

    ssh_errors = (TimeoutError, SSHException, socket.error)

    try:
        logging.info("SSHing before reboot...")
        ssh1: Result = node.run("uptime", warn=True)
    except ssh_errors as e:
        logging.warning(f"SSH before reboot failed: '{e}'")

    try:
        logging.info("Rebooting...")
        # If this succeeds, we should expect the exit code to be -1
        reboot: Result = node.sudo("reboot", warn=True)
    except ssh_errors as e:
        logging.warning(f"SSH failed, using platform to reboot: '{e}'")
        node.platform_restart()
    else:
        if reboot.exited != -1:
            logging.warning("While SSH worked, 'reboot' command failed")

    logging.info("Pinging after reboot...")
    ping2: Result = node.ping(warn=True)

    try:
        logging.info("SSHing after reboot...")
        ssh2: Result = node.run("uptime", warn=True)
    except ssh_errors as e:
        logging.warning(f"SSH after reboot failed: '{e}'")

    logging.info("Retrieving boot diagnostics...")
    node.get_boot_diagnostics()

    assert ping1.ok, f"Pinging {node.host} before reboot failed"
    if not ssh1.ok:
        logging.warning(f"SSH command '{ssh1.command}' before reboot failed")
    assert ping2.ok, f"Pinging {node.host} after reboot failed"
    if not ssh2.ok:
        logging.warning(f"SSH command '{ssh2.command}' after reboot failed")
