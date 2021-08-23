# Changelog

## [1.0.10](https://github.com/sergkr/gltflib/releases/tag/v1.0.10) - 2021-08-22

### Fixed
- Support for URL-encoded spaces (#162). See: [KhronosGroup/glTF#1449](https://github.com/KhronosGroup/glTF/issues/1449).
- BufferView.byteOffset is Optional and can be None.
- Allow comparing int-based enum with int values.

## [1.0.9](https://github.com/sergkr/gltflib/releases/tag/v1.0.9) - 2021-07-08

### Fixed
- Ensure dataclasses install requirement is only applied for Python 3.6 in setup.py (dataclasses is
  available natively in Python 3.7+). This fixes an issue that can occur when this package is
  consumed in some scenarios (e.g., executable packaging).

## [1.0.8](https://github.com/sergkr/gltflib/releases/tag/v1.0.8) - 2021-04-19

### Fixed
- Set MIME type correctly when embedding file-based image resources.

## [1.0.7](https://github.com/sergkr/gltflib/releases/tag/v1.0.7) - 2021-04-11

### Changed
- Support non-conforming glTF/GLB files with wrong encoding for JSON data. Per the spec, glTF/GLB should
use UTF-8 without BOM. However, the library now also supports reading files encoded with UTF-8 with BOM,
UTF-16-LE, UTF-16-BE, and Windows-1252.

## [1.0.6](https://github.com/sergkr/gltflib/releases/tag/v1.0.6) - 2021-02-23

### Fixed
- Fixed issue with embedding more than 2 buffers when saving GLB
- Set uri to undefined when embedding images

## [1.0.5](https://github.com/sergkr/gltflib/releases/tag/v1.0.5) - 2020-05-05

### Changed
- Emit runtime warning instead of error when encountering unexpected EOF

## [1.0.4](https://github.com/sergkr/gltflib/releases/tag/v1.0.4) - 2020-02-16

### Added
- Added roundtrip tests for all models in the
[glTF-Sample-Models](https://github.com/KhronosGroup/glTF-Sample-Models) repository
- Added "extensionsUsed" and "extensionsRequired" properties to model

### Changed
- Create missing parent directories automatically when exporting the model (and its resources)
- Retain empty strings, lists, and dictionaries in the model when exporting (only remove properties set to None, leave
everything else the same)

### Fixed
- Loosened type restrictions on "extensions" property to avoid error during load when the property is set

## [1.0.3](https://github.com/sergkr/gltflib/releases/tag/v1.0.3) - 2020-02-02

### Changed
- Emit warnings instead of errors when loading models that don't fully conform to the spec
(e.g., missing required fields), but are otherwise syntactically correct

### Fixed
- Fix loading/saving skins data (#2)
- Fix loading/saving animation samplers (#3)

## [1.0.2](https://github.com/sergkr/gltflib/releases/tag/v1.0.2) - 2019-11-20

### Changed
- Allow empty body in GLB binary chunk

## [1.0.1](https://github.com/sergkr/gltflib/releases/tag/v1.0.1) - 2019-09-07

### Changed
- Removed system-level dependency on libmagic

## [1.0.0](https://github.com/sergkr/gltflib/releases/tag/v1.0.0) - 2019-06-02

Initial release
