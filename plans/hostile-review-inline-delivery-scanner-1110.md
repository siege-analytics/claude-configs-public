# Independent metrics scanner dispositions

ACCEPT D01, D02, D03 and D04 as individual expected handled-error outcomes, not a count baseline or blanket coverage waiver. Complete selected raw output remains non-clean exit1.

D01 OSError: actual main converts reference/copy failure to return1 plus PROGRESSIVE METRICS ERROR diagnostic. Independent injected OSError control passed. A missing source returning successful metrics falsifies this acceptance.

D02 ValueError: actual main converts invalid reference data to return1 plus diagnostic. Independent injected ValueError control passed; separate independent nine-case runtime review also exercised nonregular FIFO refusal. Invalid canonical input accepted as success falsifies this disposition.

D03 SubprocessError: actual main converts selector process failure to return1 plus diagnostic. Independent injected SubprocessError control passed. Failed selection producing successful metrics falsifies it.

D04 JSONDecodeError: actual main converts malformed selector data to return1 plus diagnostic. Independent injected JSONDecodeError control passed. Malformed data reported as success or silently accepted stale output falsifies it.

The controls invoke production main and replace its build boundary, not its error handling. I reran all four successfully and inspected caller flow: serial(build()) must complete before comparison or writing, and __main__ exits with main's result. The classifier expects pytest.raises although this CLI consumes errors into a failure status; return/diagnostic assertions are appropriate. These controls do not establish each originating error context. The main AST equality to protected develop is corroboration only, not a grandfathering reason. No source edits, suppression, ignore or exit mapping were introduced by this review. Prior source/metrics correctness approval is separate.

bin/progressive-loading-metrics.py SHA256 23ffecea0a767b80140ea72fd3cb9e1396cd33b586d094ea6e5d5b35d7ee452b

bin/_test/inline_delivery_test.py SHA256 a85ffcf399f8613a7167a51dbceddf1d0bffde7144e3aae2a15935b3994c24d2

.claude/scanner-test-map.json SHA256 5da6bc87e51adee6010a4ff2fdfab9957ed8ae99c2767eea6f99d5966c695886

cap-selected-mapped-scan.log SHA256 17a13b53b6d8e8e7db65d820a5142d8043a9afc989b22e2c2a91746e7ff3e047

metrics-error-contract-controls.py SHA256 92807a2529bcf9cb5e46c406e5c201c08749f1c810046e7e623c1658194442fd

Final evidence-only snapshot requires reconciliation; changed source/test/scanner/map pins require renewed review. No live-host or installation approval is conveyed.
