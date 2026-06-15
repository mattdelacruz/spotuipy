#!/usr/bin/env bash
#
# run_tests.sh — run the spotuipy unit test suite with labelled sections.
#
# Each test file covers one area of the codebase. This script runs them one
# group at a time with a header describing what that group verifies, then
# prints a combined summary at the end.
#
# Usage:
#   ./run_tests.sh           # run everything
#   ./run_tests.sh -q        # quieter (less per-test output)

set -u

# Resolve the project root (directory this script lives in) so the script
# works regardless of where it's called from.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

# Pick the pytest verbosity: -v by default, -q if the user passed -q.
PYTEST_FLAGS="-v"
if [[ "${1:-}" == "-q" ]]; then
    PYTEST_FLAGS="-q"
fi

# Make sure pytest is available before doing anything else.
if ! python3 -m pytest --version >/dev/null 2>&1; then
    echo "pytest is not installed. Install it with:"
    echo "    pip install pytest"
    exit 1
fi

# A test group is: "file::Human-readable description of what it verifies".
TEST_GROUPS=(
    "tests/test_track.py::Track data model — lookups, ordering, and that missing keys return None instead of raising"
    "tests/test_ended_naturally.py::Natural-end heuristic — distinguishes a track finishing on its own from a manual skip"
    "tests/test_device_selection.py::Device selection — preference order (spotifyd, then active, then first available)"
)

divider() {
    printf '%s\n' "------------------------------------------------------------"
}

overall_status=0

for group in "${TEST_GROUPS[@]}"; do
    file="${group%%::*}"
    label="${group##*::}"

    divider
    echo "RUNNING: $file"
    echo "VERIFIES: $label"
    divider

    python3 -m pytest "$file" $PYTEST_FLAGS
    status=$?
    if [[ $status -ne 0 ]]; then
        overall_status=1
        echo ">>> FAILURES in $file"
    fi
    echo
done

# Combined summary line across the whole suite.
divider
echo "COMBINED SUMMARY"
divider
python3 -m pytest tests/ -q

if [[ $overall_status -eq 0 ]]; then
    echo
    echo "All test groups passed."
else
    echo
    echo "One or more test groups had failures (see above)."
fi

exit $overall_status