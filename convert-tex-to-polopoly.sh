#!/bin/bash
# Usage: convert-tex-to-polopoly.sh [in.tex] > out.html

# A better idea is perhaps to use pandoc:
#
#    pandoc --from latex --to html5 --no-highlight --mathjax
#
# or make4ht:
#
#    make4ht filename.tex "mathjax"
#
# Or find some other solution, such as:
#
#    https://github.com/jipsen/latexmathjax


split_paragraphs () {
    # Remove single line breaks
    # Convert 2+ line breaks into <p>...</p>
	LF='
'
	XEOL=$(echo -e -n "\x1")

    # Convert \n to \x1
	tr "$LF" "$XEOL" |
    # Remove trailing \x1; 2 or more \x1 => \n; \x1 => space
    sed -E -e "s/$XEOL+$//g" -e "s/$XEOL$XEOL+/\\$LF/g" -e "s/$XEOL/ /g" |
    # LINE => <p>LINE</p>
    sed -e 's/^\(.*\)$/<p>\1<\/p>/g'
}

# Split into paragraphs.
# Replace $...$ with <span class="math-tex">\(...\)</span>
# Replace \emph{...} and \textit{...} with <i>...</i>
# Replace ``...'' with curly quotation marks (UTF8: \xE2\x80\x9C and \x9D)
# Replace "\ " and "~" with (non-breaking) space.
BQ='`'
FQ="'"

cat "$@" | split_paragraphs |
sed -E -e 's/\$([^$]*)\$/<span\ class="math-tex">\\(\1\\)<\/span>/g' \
	   -e 's/\\(emph|textit){([^}]*)}/<i>\2<\/i>/g' \
	   -e "s/$BQ$BQ([^$BQ$FQ]*)$FQ$FQ/“\1”/g" \
	   -e "s/$BQ([^$BQ$FQ]*)$FQ/‘\1’/g" \
       -e 's/([^\\])\\ /\1 /g' -e 's/~/\&nbsp;/g'
