# Changelog

## [1.0.5] - 2020-05-05

### Changed
- Emit runtime warning instead of error when encountering unexpected EOF

## [1.0.4] - 2020-02-16

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

## [1.0.3] - 2020-02-02

### Changed
- Emit warnings instead of errors when loading models that don't fully conform to the spec
(e.g., missing required fields), but are otherwise syntactically correct

### Fixed
- Fix loading/saving skins data (#2)
- Fix loading/saving animation samplers (#3)

## [1.0.2] - 2019-11-20

### Changed
- Allow empty body in GLB binary chunk

## [1.0.1] - 2019-09-07

### Changed
- Removed system-level dependency on libmagic

## [1.0.0] - 2019-06-02

Initial release
