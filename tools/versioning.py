import pathlib
import re

from hatchling.metadata.core import ProjectMetadata
from hatchling.plugin.manager import PluginManager


def get_version():
    root = pathlib.Path(__file__).parent.parent
    plugin_manager = PluginManager()
    metadata = ProjectMetadata(root, plugin_manager)

    source = metadata.hatch.version.source

    version_data = source.get_version_data()
    return version_data["version"]


def write_toml(filepath="pyproject.toml", source="scm"):
    with open(filepath, "r") as infile:
        contents = infile.read()

    pattern = r"(\[tool\.hatch\.version\]\s)([\s\S]*?)(\s+\[tool\.versioningit\])"
    if source == "scm":
        replacement = 'source = "versioningit"'
    else:
        replacement = 'path = "mox/__version__.py"\nscheme = "semver"'

    new_contents = re.sub(pattern, r"\1" + replacement + r"\3", contents, flags=re.DOTALL)
    with open(filepath, "w") as outfile:
        outfile.writelines(new_contents)


def main():
    print(get_version())


if __name__ == "__main__":
    main()
