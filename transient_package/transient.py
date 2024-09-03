import importlib.metadata
import os
import tempfile
import typing
import wheel.wheelfile

# Set the package name to "transient_package" if it's not already defined
if not __package__:
  package = "transient_package"

# Attempt to retrieve the package version or use "0.0.0" as a fallback
try:
  __version__ = importlib.metadata.version(__package__)
except importlib.metadata.PackageNotFoundError:
  __version__ = "0.0.0"

# Generator string as in the wheel metadata
TRANSIENT_GENERATOR = f"Generator: {__package__}"

def create_transient_package(name: str,
                             version: str,
                             requirements: typing.List[str],
                             target: str,
                             *,
                             tag: str = "py3-none-any"):
  """
    Create a transient wheel package and return it as a bytes object.

    Parameters
    ----------
    name         : str
                   The name of the package.
    version      : str
                   The version of the package.
    requirements : List[str]
                   The list of package requirements.
    target       : str
                   The output directory where the package will be saved.
    tag          : str
                   The wheel tag (e.g., "py3-none-any").
  """

  # Create a temporary directory for the package files
  with tempfile.TemporaryDirectory() as directory:
    # Define the path for the wheel file
    wheel_file = os.path.join(target, f"{name}-{version}-{tag}.whl")

    # Create the .dist-info directory inside the source directory
    dist_info = os.path.join(directory, f"{name}-{version}.dist-info")
    os.makedirs(dist_info)

    # Write package metadata to the METADATA file
    with open(os.path.join(dist_info, "METADATA"), "w") as file:
      file.write("Metadata-Version: 2.1\n")
      file.write(f"Name: {name}\n")
      file.write(f"Version: {version}\n")
      for requirement in requirements:
        file.write(f"Requires-Dist: {requirement}\n")
      file.write("\n")

    # Create an empty top_level.txt file
    with open(os.path.join(dist_info, "top_level.txt"), "w") as file:
      file.write("\n")

    # Write wheel metadata to the WHEEL file
    with open(os.path.join(dist_info, "WHEEL"), "w") as file:
      file.write("Wheel-Version: 1.0\n")
      file.write(f"Generator: {__package__} ({__version__})\n")
      file.write("Root-Is-Purelib: true\n")
      file.write(f"Tag: {tag}\n")
      file.write("\n")

    # Create the wheel file from the source directory
    with wheel.wheelfile.WheelFile(wheel_file, "w") as whl:
      whl.write_files(directory)
