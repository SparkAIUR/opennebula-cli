"""Independently materialized OpenNebula server capability profiles."""

from __future__ import annotations

import re
from importlib.resources import files
from typing import Final, Literal

from opennebula_cli.registry.schema import VersionProfileCatalog
from opennebula_cli.sdk.exceptions import UnsupportedCapabilityError
from opennebula_cli.sdk.models.system import CapabilityProfile

ProfileName = Literal["7.0", "7.4"]

COMMON_METHODS: Final[frozenset[str]] = frozenset(
    {
        "one.system.version",
        "one.vm.info",
        "one.vmpool.info",
        "one.vmpool.infoextended",
        "one.host.info",
        "one.hostpool.info",
        "one.image.info",
        "one.imagepool.info",
        "one.template.info",
        "one.templatepool.info",
        "one.vn.info",
        "one.vnpool.info",
        "one.datastore.info",
        "one.datastorepool.info",
        "one.cluster.info",
        "one.clusterpool.info",
        "one.acl.info",
    }
)

V7_0_ONLY_METHODS: Final[frozenset[str]] = frozenset(
    {"official.onevnet.addleases", "official.onevnet.rmleases"}
)

V7_4_METHODS: Final[frozenset[str]] = frozenset(
    {
        "one.cluster.optimize",
        "one.cluster.plandelete",
        "one.cluster.planexecute",
        "one.group.vlan",
        "one.vm.exec",
        "one.vm.retryexec",
        "one.vm.cancelexec",
        "one.vm.vmgroupadd",
        "one.vm.vmgroupdel",
        "oneflow.sched_delete",
        "oneform.v1",
    }
)

_VERSION_PATTERN = re.compile(r"^\s*(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?")


def catalog_for_profile(profile: ProfileName) -> VersionProfileCatalog:
    """Load the shipped catalog for an exact compatibility profile."""

    filename = f"v{profile.replace('.', '_')}.yaml"
    resource = files("opennebula_cli.catalogs.profiles").joinpath(filename)
    with resource.open("rb") as profile_file:
        import yaml

        return VersionProfileCatalog.model_validate(yaml.safe_load(profile_file))


def commands_for_profile(profile: ProfileName) -> dict[str, set[str]]:
    """Return complete family command sets without inheriting another profile."""

    catalog = catalog_for_profile(profile)
    return {family: set(commands) for family, commands in catalog.commands.items()}


def profile_for_version(version: str) -> CapabilityProfile:
    """Select a supported profile from authenticated server version text."""

    match = _VERSION_PATTERN.match(version)
    if match is None:
        raise UnsupportedCapabilityError(f"Malformed OpenNebula server version: {version!r}")
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    if (major, minor) == (7, 0):
        return CapabilityProfile(
            name="7.0",
            server_version=version.strip(),
            methods=COMMON_METHODS | V7_0_ONLY_METHODS,
        )
    if (major, minor) == (7, 4):
        return CapabilityProfile(
            name="7.4",
            server_version=version.strip(),
            methods=COMMON_METHODS | V7_4_METHODS,
        )
    raise UnsupportedCapabilityError(
        f"Unsupported OpenNebula server line {major}.{minor}; supported profiles are 7.0 and 7.4."
    )
