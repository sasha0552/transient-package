import click
import functools
import glob
import logging
import os
import packaging.version
import subprocess
import sys
import tempfile
import traceback

from ..transient import TRANSIENT_GENERATOR, create_transient_package

# Configure logging
logging.basicConfig(format="[%(levelname)s] %(asctime)s  %(message)s", level=logging.INFO)

# Create a logger object for this module
logger = logging.getLogger(__name__)

##### ##### ##### ##### #####

def create_options(func):
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

def pip_options(func):
  @click.option(
    "-i",
    "--interpreter",
    default=sys.executable,
    help="""
      Path to the Python interpreter to be used when calling pip
    """,
  )
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    return func(*args, **kwargs)
  return wrapper

##### ##### ##### ##### #####

def _invoke_code(interpreter, code):
  # Run the provided code using the specified interpreter and capture the output
  output = subprocess.check_output([interpreter, "-c", code], stderr=subprocess.DEVNULL)

  # Decode and return the output as a string, stripping any trailing whitespace
  return output.decode("utf-8").rstrip()

def _log_and_exit(*args, **kwargs):
  # Log error if the uninstallation failed
  logger.error(*args, **kwargs)

  # Capture and format the exception information
  exc_type, exc_value, _trace = sys.exc_info()
  exc_desc_lines = traceback.format_exception_only(exc_type, exc_value)
  exc_desc = "".join(exc_desc_lines).rstrip()

  # Log the exception details
  logger.error(exc_desc)

  # Exit the script with an error status
  sys.exit(1)

def _create(source, source_version, target, target_version, output_directory):
  # Check if the target version is not a specifier
  if target_version and any(char in target_version for char in [ "!", ",", "<", "=", ">", "~" ]):
    # Format it as a specifier
    target_version = f"=={target_version}"

  # Generate the transient package and write it to the target directory
  create_transient_package(
    name=source,
    version=source_version or "0.0.0",
    requirements=[
      target + target_version if target_version else target,
    ],
    target=output_directory,
  )

  # Log the creation of the transient package
  logger.info("created transient package '%s'", source)

def _install(source, source_version, target, target_version, interpreter):
  # Initialize flag to track if source package is installed
  source_installed = False

  # Detect the source version if not provided
  if source_version is None:
    try:
      # Retrieve the version of the source package
      source_version = _invoke_code(interpreter, f"import importlib.metadata; print(importlib.metadata.version('{source}'))")

      # Mark source package as installed
      source_installed = True

      # Log detected source package version
      logger.info("detected '%s' with version '%s'", source, source_version)

      # If target version is not provided
      if target_version is None:
        # Parse the source version string into a Version object
        src = packaging.version.Version(source_version)

        # Define minimum and maximum version strings
        tgt = f"{src.major}.{src.minor}.{src.micro}"
        tgt = f"{src.major}.{src.minor}.{src.micro + 1}"

        # Update the specifier with the version range that includes all post-releases
        target_version = f">={tgt_min},<{tgt_max}" 
    except subprocess.CalledProcessError:
      # Proceed if source package is not installed
      pass

  if source_installed:
    try:
      # Uninstall the source package
      subprocess.check_call([interpreter, "-m", "pip", "uninstall", "--yes", source])
    except subprocess.CalledProcessError:
      _log_and_exit("failed to uninstall '%s'", source)

    # Log the uninstallation of the source package
    logger.info("uninstalled source package '%s'", source)

  # Create a temporary directory for the transient package
  with tempfile.TemporaryDirectory() as directory:
    # Create the transient package
    _create(source, source_version, target, target_version, directory)

    # Find the created wheel file
    wheel_file = glob.glob(os.path.join(directory, "*.whl"))[0]

    try:
      # Install the transient package
      subprocess.check_call([interpreter, "-m", "pip", "install", wheel_file])
    except subprocess.CalledProcessError:
      _log_and_exit("failed to install '%s'", source)

    # Log the installation of the transient package
    logger.info("installed transient package '%s'", source)

def _uninstall(interpreter, package):
  try:
    # Retrieve the wheel metadata for the specified package
    wheel = _invoke_code(interpreter, f"import importlib.metadata; print(importlib.metadata.distribution('{package}').read_text('WHEEL'))")
  except subprocess.CalledProcessError:
    _log_and_exit("package '%s' not found", package)

  # Check if the package is transient
  if TRANSIENT_GENERATOR in wheel:
    try:
      # Uninstall the transient package
      subprocess.check_call([interpreter, "-m", "pip", "uninstall", "--yes", package])
    except subprocess.CalledProcessError:
      _log_and_exit("failed to uninstall '%s'", package)

    # Log successful uninstallation of transient package
    logger.info("uninstalled transient package '%s'", package)
  else:
    # Log error if the package is not transient
    logger.error("package '%s' is not transient", package)

    # Exit the script with an error status
    sys.exit(1)

##### ##### ##### ##### #####

@click.group()
def main():
  pass

@main.command()
@create_options
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
@create_options
@pip_options
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
  version, but will also include all post-releases.

  If detection is unsuccessful, the command defaults to using the latest version.

  This command uninstalls the source package before proceeding.
  """

  return _install(*args, **kwargs)

@main.command()
@pip_options
@click.argument("package")
def uninstall(*args, **kwargs):
  """
  Uninstall transient package.

  This command uninstalls transient packages. It does nothing with
  non-transient packages.
  """

  return _uninstall(*args, **kwargs)

##### ##### ##### ##### #####

#
if __name__ == "__main__":
  main()
