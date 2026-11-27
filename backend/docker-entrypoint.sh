set -eu

if [ -n "${GOOGLE_CREDENTIALS_JSON:-}" ]; then
  umask 077
  credentials="$(mktemp)"
  printf '%s' "$GOOGLE_CREDENTIALS_JSON" > "$credentials"
  export GOOGLE_APPLICATION_CREDENTIALS="$credentials"
  unset GOOGLE_CREDENTIALS_JSON
fi

case "${1:-api}" in
  api)
    exec uvicorn app.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --proxy-headers \
      --forwarded-allow-ips "$FORWARDED_ALLOW_IPS" \
      --workers "$WEB_CONCURRENCY" \
      --timeout-keep-alive 65 \
      --timeout-graceful-shutdown 25 \
      --no-access-log
    ;;
  worker)
    exec python -m app.worker
    ;;
  migrate)
    exec alembic upgrade head
    ;;
  *)
    exec "$@"
    ;;
esac
