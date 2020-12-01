# deriva-workbench

Schema workbench for DERIVA platform. This application can be used to browse 
and update DERIVA catalog annotations. Currently, this project is availabe as a 
**development preview** only.

## Requirements

* Python 3.x
* PyQt5 (5.11.3+)
* PyQtWebEngine (5.12.1+)
* The application has been tested on Mac OS though it should work on Windows and Linux.

## Installation

These steps assume you have a recent Python 3.x environment installed. Next, 
install the PyQt dependencies.

```shell script
$ pip3 install --upgrade PyQt5
$ pip3 install --upgrade PyQtWebEngine
```

Install the `deriva-workbench` from its GIT repository.

```shell script
$ pip3 install --upgrade git+https://github.com/informatics-isi-edu/deriva-workbench
```

## Usage

Start the application from the command-line.

```shell script
$ deriva-workbench
```

See [usage document](./docs/usage.md) for more information.
