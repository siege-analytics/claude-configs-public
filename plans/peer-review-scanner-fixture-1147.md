# Independent scanner fixture correction

ACCEPT the fixture-only correction in test_json_map_does_not_require_a_toml_parser. The production helper resolves its source and discovered test paths; the old expectation compared a lexical macOS /var alias with a canonical /private/var path. The new expectation resolves the same actual fixture file and also tests a separate repo-alias symlink. Both source spellings must locate that exact test file while TOML imports remain unavailable. No assertion is removed or bypassed, and no production scanner source changes.

Independent focused execution passed one method in0.117s using Homebrew Python. This is an appropriate correction of the test oracle and adds alias coverage. The failed nineteen-group producer remains historical failure evidence; its replacement run must complete before any aggregate-pass claim. Final selected scan and nine-input evidence binding remain coordinator work.

Fixture SHA256: ff66a6252cc5fee4cdce7634e024928c4cae96037b2b00da43a72abdb1823de1

Verified-by: python3 -B bin/_test/scanner_source_test.py ScannerSourceTest.test_json_map_does_not_require_a_toml_parser (independentPASS); exact diff and helper source inspection.
