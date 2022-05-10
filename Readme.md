# ENRE-py

ENRE (ENtity Relationship Extractor) is a tool for extraction of code entity dependencies or relationships from source code. The resolved python entity types include:

|Entity Type|
|-|
|Package|
|Module|
|Class|
|Function|
|Variable|
|Parameter|
|Variable|
|Module Alias|

The resolved dependency types include:


|Dependency Type|
|-|
|Import|
|Inherit|
|Define|
|Call|
|Use|
|Set|
|Alias To|

For more detailed information on python entities and dependencies, see the [doc](./doc) to get definitions and examples.

## Usage

You can use enre to analyze a python package:
```
./enre.exe <dir>
```

or a python module:
```
./enre.exe <py-file>
```