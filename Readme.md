# ENRE-py

ENRE (ENtity Relationship Extractor) is a tool for extraction of code entity dependencies or relationships from source code. The resolved python entity types include:


For more detailed information on python entities and dependencies, see the [doc](./docs) to get definitions and examples.
## Features
- Control flow analysis for python

## Supported Language
|Language|Supported Version|
|-|-|
|Python|3.x|

## Getting Started
> ENRE-python has been tested to be worked with python3.x.




## Usage
Use `-h` or `--help` option to check usable options.
```shell
usage: enre.exe [-h] [--profile] [--cfg] [--compatible] [--builtins BUILTINS] [--cg] [root path]

positional arguments:
  root path            root package path

options:
  -h, --help           show this help message and exit
  --profile            output consumed time in json format
  --cfg                run control flow analysis and output module summaries
  --compatible         output compatible format
  --builtins BUILTINS  builtins module path
  --cg                 dump call graph in json

```

- You can use enre to analyze a python package:
```
enre.exe <dir>
```

- Analyzing a single python module:
```
enre.exe <py-file>
```

- Use control flow functionality to get more accurate dependency.
```shell
enre.exe <dir> --cfg
```

- Output call graph when after control flow analysis
```shell
enre.exe <dir> --cfg --cg
```

## Documentation

Check the [doc](./docs) to get detail about entities and dependencies.

## Building
Use Pyinstaller to build enre into executable binary:
```shell
pyinstaller -F .\enre\__main__.py
```

