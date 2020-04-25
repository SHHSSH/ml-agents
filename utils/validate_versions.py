#!/usr/bin/env python3

import os
import json
import sys
from typing import Dict, Optional
import argparse

VERSION_LINE_START = "__version__ = "

DIRECTORIES = [
    "ml-agents/mlagents/trainers",
    "ml-agents-envs/mlagents_envs",
    "gym-unity/gym_unity",
]

UNITY_PACKAGE_JSON_PATH = "com.unity.ml-agents/package.json"
ACADEMY_PATH = "com.unity.ml-agents/Runtime/Academy.cs"

PYTHON_VERSION_FILE_TEMPLATE = """
# Version of the library that will be used to upload to pypi
__version__ = {version}

# Git tag that will be checked to determine whether to trigger upload to pypi
__release_tag__ = {release_tag}
"""


def _escape_non_none(s: Optional[str]) -> str:
    """
    Returns s escaped in quotes if it is non-None, else "None"
    :param s:
    :return:
    """
    if s is not None:
        return f'"{s}"'
    else:
        return "None"


def extract_version_string(filename):
    with open(filename) as f:
        for l in f.readlines():
            if l.startswith(VERSION_LINE_START):
                return l.replace(VERSION_LINE_START, "").strip()
    return None


def check_versions() -> bool:
    version_by_dir: Dict[str, str] = {}
    for directory in DIRECTORIES:
        path = os.path.join(directory, "__init__.py")
        version = extract_version_string(path)
        print(f"Found version {version} for {directory}")
        version_by_dir[directory] = version

    # Make sure we have exactly one version, and it's not none
    versions = set(version_by_dir.values())
    if len(versions) != 1 or None in versions:
        print("Each setup.py must have the same VERSION string.")
        return False
    return True


def set_version(python_version: str, csharp_version: str, release_tag: str) -> None:
    new_contents = PYTHON_VERSION_FILE_TEMPLATE.format(
        version=_escape_non_none(python_version),
        release_tag=_escape_non_none(release_tag),
    )
    for directory in DIRECTORIES:
        path = os.path.join(directory, "__init__.py")
        print(f"Setting {path} to version {python_version}")
        with open(path, "w") as f:
            f.write(new_contents)

    if csharp_version is not None:
        package_version = csharp_version + "-preview"
        print(
            f"Setting package version to {package_version} in {UNITY_PACKAGE_JSON_PATH}"
        )
        set_package_version(package_version)
        print(f"Setting package version to {package_version} in {ACADEMY_PATH}")
        set_academy_version_string(package_version)


def set_package_version(new_version: str) -> None:
    with open(UNITY_PACKAGE_JSON_PATH, "r") as f:
        package_json = json.load(f)
    if "version" in package_json:
        package_json["version"] = new_version
    with open(UNITY_PACKAGE_JSON_PATH, "w") as f:
        json.dump(package_json, f, indent=2)


def set_academy_version_string(new_version):
    needle = "internal const string k_PackageVersion"
    found = 0
    with open(ACADEMY_PATH) as f:
        lines = f.readlines()
    for i, l in enumerate(lines):
        if needle in l:
            left, right = l.split(" = ")
            right = f' = "{new_version}";\n'
            lines[i] = left + right
            found += 1
    if found != 1:
        raise RuntimeError(
            f'Expected to find search string "{needle}" exactly once, but found it {found} times'
        )
    with open(ACADEMY_PATH, "w") as f:
        f.writelines(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-version", default=None)
    parser.add_argument("--csharp-version", default=None)
    parser.add_argument("--release-tag", default=None)
    # unused, but allows precommit to pass filenames
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    if args.python_version:
        print(f"Updating python library to version {args.python_version}")
        if args.csharp_version:
            print(f"Updating C# package to version {args.csharp_version}")
        set_version(args.python_version, args.csharp_version, args.release_tag)
    else:
        ok = check_versions()
        return_code = 0 if ok else 1
        sys.exit(return_code)
