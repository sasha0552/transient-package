import click
import functools
import glob
import importlib.metadata
import logging
import os
import subprocess
import sys
import tempfile

from ..transient import TRANSIENT_GENERATOR, create_transient_package

# Configure logging
logging.basicConfig(format="[%(levelname)s] %(asctime)s  %(message)s", level=logging.INFO)

# Create a logger object for this module
logger = logging.getLogger(__name__)

##### ##### ##### ##### #####

def create_params(func):
  @click.option(
    "-s",
    "--source",
    help="""
      Name of the transient package to be created
    """,
    required=True,
  )
  @click.option(
    "-sv",
    "--source-version",
    help="""
      Version of the transient package to be created
    """,
  )
  @click.option(
    "-t",
    "--target",
    help="""
      Name of the target package that the transient package will depend on
    """,
    required=True,
  )
  @click.option(
    "-tv",
    "--target-version",
    help="""
      Version of the target package that the transient package will depend on
    """,
  )
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    return func(*args, **kwargs)
  return wrapper

##### ##### ##### ##### #####

def _create(source, source_version, target, target_version, output_directory):
  # Generate the transient package and write it to the target directory
  create_transient_package(
    name=source,
    version=source_version or "0.0.0",
    requirements=[
      f"{target}=={target_version}" if target_version else target,
    ],
    target=output_directory,
  )

  # Log the creation of the transient package
  logger.info("created transient package '%s'", source)

def _install(source, source_version, target, target_version):
  # Detect the source version if not provided
  if source_version is None:
    try:
      # Retrieve the version of the source package
      source_version = importlib.metadata.version(source)

      # Log detected source package version
      logger.info("detected '%s' with version '%s'", source, source_version)

      # If target version is not provided
      if target_version is None:
        # Use the source version
        target_version = source_version
    except importlib.metadata.PackageNotFoundError:
      # Proceed if source package is not installed
      pass

  try:
    # Check if the source package is installed
    importlib.metadata.version(source)

    # Uninstall the source package
    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "--yes", source])

    # Log the uninstallation of the source package
    logger.info("uninstalled source package '%s'", source)
  except importlib.metadata.PackageNotFoundError:
    # Proceed if source package is not installed
    pass

  # Create a temporary directory for the transient package
  with tempfile.TemporaryDirectory() as directory:
    # Create the transient package
    _create(source, source_version, target, target_version, directory)

    # Find the created wheel file
    wheel_file = glob.glob(os.path.join(directory, "*.whl"))[0]

    # Install the transient package
    subprocess.check_call([sys.executable, "-m", "pip", "install", wheel_file])

    # Log the installation of the transient package
    logger.info("installed transient package '%s'", source)

def _uninstall(package):
  try:
    # Retrieve the distribution metadata for the specified package
    distribution = importlib.metadata.distribution(package)
    
    # Read the WHEEL file from the distribution
    wheel = distribution.read_text("WHEEL")

    # Check if the package is transient
    if TRANSIENT_GENERATOR in wheel:
      # Uninstall the transient package
      subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "--yes", package])

      # Log successful uninstallation of transient package
      logger.info("uninstalled transient package '%s'", package)
    else:
      # Log error if the package is not transient
      logger.error("package '%s' is not transient", package)
  except importlib.metadata.PackageNotFoundError:
    # Log error if the package was not found
    logger.error("package '%s' not found", package)

##### ##### ##### ##### #####

@click.group()
def main():
  pass

@main.command()
@create_params
@click.option(
  "-od",
  "--output-directory",
  help="""
    Directory path where the output wheel file will be saved
  """,
  required=True,
  type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
def create(*args, **kwargs):
  """
  Generate transient package.

  This command generates "transient" packages, which are essentially empty
  packages designed to depend on a specified "target" package that replaces an
  existing "source" package.

  If the source package version is not specified, it defaults to "0.0.0".

  If the target package version is not specified, it defaults to the latest
  version.
  """

  return _create(*args, **kwargs)

@main.command()
@create_params
def install(*args, **kwargs):
  """
  Generate and install transient package.

  This command generates "transient" packages, which are essentially empty
  packages designed to depend on a specified "target" package that replaces an
  existing "source" package, and installs it.

  If the source package version is not provided, the command will try to
  detect it automatically.

  If detection is unsuccessful, the version defaults to "0.0.0".

  If the target package version is not specified and the source package
  version is successfully detected, the command will use the source package
  version.

  If detection is unsuccessful, the command defaults to using the latest version.

  This command uninstalls the source package before proceeding.
  """

  return _install(*args, **kwargs)

@main.command()
@click.argument("package")
def uninstall(*args, **kwargs):
  """
  Uninstall transient package.

  This command uninstalls transient packages. It does nothing with
  non-transient packages.
  """

  return _uninstall(*args, **kwargs)
