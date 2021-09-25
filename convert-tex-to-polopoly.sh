#/bin/bash
# Usage: convert-tex-to-polopoly.sh in.tex > out.html

sed -e 's/\$\([^$]*\)\$/<span\ class="math-tex">\\(\1\\)<\/span>/g' "$@"

# TODO:
# Convert \emph{...} -> <i>...</i>
# Remove single line breaks
# Convert double line break to <p>...</p>
