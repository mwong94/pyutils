# generate bin/ symlinks so every executable script is callable via one PATH entry
link:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{justfile_directory()}}"
    rm -rf bin
    mkdir -p bin
    for f in */*.py */*.sh; do
        [ -x "$f" ] || continue
        ln -s "../$f" "bin/$(basename "$f")"
    done
    echo "linked $(find bin -type l | wc -l) scripts into bin/"
