set -eu

: "${BACKEND_URL:?set BACKEND_URL to the API address, for example http://api:8000}"

case "$BACKEND_URL" in
  *'|'* | *'&'* | *\\* | *' '*)
    echo "BACKEND_URL may not contain |, &, a backslash or a space" >&2
    exit 64
    ;;
  http://?* | https://?*) ;;
  *)
    echo "BACKEND_URL must start with http:// or https://" >&2
    exit 64
    ;;
esac

target="${BACKEND_URL%/}"
rendered="$(mktemp)"
while IFS= read -r file; do
  sed "s|$BACKEND_URL_PLACEHOLDER|$target|g" "$file" > "$rendered"
  cat "$rendered" > "$file"
done < .backend-url-files
rm -f "$rendered"

exec node server.js
