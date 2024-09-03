# transient-package

CLI utility for creating transient Python packages.

## Installation

```sh
pip install transient-package
```

## Usage

### Create a transient package

```sh
transient-package create \
  --source triton        \
  --target triton-pascal \
  --output-directory .
```

#### Result

A `triton` package with version `0.0.0` will be created, which depends on the `triton-pascal` package.

### Create a transient package with explicit versions

```sh
transient-package create \
  --source triton        \
  --source-version 3.0.0 \
  --target triton-pascal \
  --target-version 3.0.0 \
  --output-directory .
```

#### Result

A `triton` package with version `3.0.0` will be created, which depends on the `triton-pascal` package with version `3.0.0`.

### Create a transient package and install it

```sh
$ transient-package install \
  --source triton         \
  --target triton-pascal
```

#### Result

##### If the source package is not installed

A `triton` package with version `0.0.0` will be installed, which depends on the `triton-pascal` package.

##### If the source package is installed

A `triton` package with version `<source package version>` will be installed, which depends on the `triton-pascal` package with version `<source package version>`.

The source package will be uninstalled before installing the transient package.

### Remove a transient package

```sh
transient-package uninstall triton
```

#### Result

If the `triton` package is installed and transient, it will be removed.
