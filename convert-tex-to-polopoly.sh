#/bin/bash
# Usage: convert-tex-to-polopoly.sh in.tex > out.html

sed -e 's/\$\([^$]*\)\$/<span\ class="math-tex">\\(\1\\)<\/span>/g' \
	-e 's/\\emph{\([^}]*\)}/<i>\1<\/i>/g' \
	-e 's/\\textit{\([^}]*\)}/<i>\1<\/i>/g' \
	"$@"

# TODO:
# Remove single line breaks
# Convert double line break to <p>...</p>
