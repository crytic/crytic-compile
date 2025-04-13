#!/usr/bin/env bash

DIR=$(mktemp -d)

normalize_file() {
    JQ_SCRIPT=$(cat <<'EOF'
def sort_deps:
  if type == "object" then
    # Process each key-value pair
    to_entries | map(
      if .key == "contractDependencies" and (.value | type == "array") then
        .value = (.value | sort)
      else
        .value = (.value | sort_deps)
      end
    ) | from_entries
  elif type == "array" then
    # Process each array element recursively
    map(sort_deps)
  else
    .
  end;

sort_deps
EOF
)

    jq "$JQ_SCRIPT" "$1" > "$1.mod"
    mv "$1.mod" "$1"
}

cp -r tests/solc-multi-file "$DIR"
cd "$DIR/solc-multi-file" || exit 255
crytic-compile --compile-remove-metadata --export-formats solc,truffle A.sol

cd - || exit 255
node tests/process_combined_solc.js "$DIR/solc-multi-file/crytic-export/combined_solc.json" "$DIR"

case "$(uname -sr)" in
    #for some reason, contractDependencies appear in random order in Windows
    #so we sort them for consistency in the tests
    CYGWIN*|MINGW*|MSYS*)
        echo "Testing on Windows, doing extra JSON normalization"
        for f in "$DIR/solc-multi-file/crytic-export/"*.json tests/expected/solc-multi-file/*.json; do
            normalize_file "$f"
        done
    ;;
esac

DIFF=$(diff -r "$DIR/solc-multi-file/crytic-export" tests/expected/solc-multi-file)
if [ "$?" != "0" ] || [ "$DIFF" != "" ]
then  
    echo "solc-multi-file test failed"
    echo "$DIFF"
    exit 255
fi
