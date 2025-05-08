#!/bin/bash

# sed -r 's/\x1B\\[[0-9;]*[a-zA-Z]//g'
# perl -pe 's/\e\\[[0-9;]*[a-zA-Z]//g' | cut -d ' ' -f1
# cat | tee /dev/stderr | perl -pe 's/\e\\[[0-9;]*[a-zA-Z]//g'\

# Linux compatible ANSI stripper
# perl -pe 's/\x1b\\[[0-9;]*[mGKFJH]?//g' | cut -d ' ' -f1


# macOS-compatible ANSI stripper
#perl -pe 's/\x1b\[[0-9;]*[mGKFJH]?//g' | cut -d ' ' -f 1

if [[ "$(uname)" == "Darwin" ]]; then
  # macOS (BSD-style tools)
  perl -pe 's/\x1b\[[0-9;]*[mGKFJH]?//g' | cut -d ' ' -f 1
else
  # Linux (GNU-style tools)
  perl -pe 's/\e\[[0-9;]*[a-zA-Z]//g' | cut -d ' ' -f 1
fi