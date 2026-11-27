import type { IdentityProviderName } from "@/lib/api/types";

const MARK = "size-4.5 flex-none";

function GoogleMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" className={MARK}>
      <path
        className="fill-google-red"
        d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
      />
      <path
        className="fill-google-blue"
        d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
      />
      <path
        className="fill-google-yellow"
        d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
      />
      <path
        className="fill-google-green"
        d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
      />
    </svg>
  );
}

function MicrosoftMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 21 21" className={MARK}>
      <rect className="fill-microsoft-red" x="1" y="1" width="9" height="9" />
      <rect className="fill-microsoft-green" x="11" y="1" width="9" height="9" />
      <rect className="fill-microsoft-blue" x="1" y="11" width="9" height="9" />
      <rect className="fill-microsoft-yellow" x="11" y="11" width="9" height="9" />
    </svg>
  );
}

function YahooMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className={MARK}>
      <rect className="fill-yahoo" width="24" height="24" rx="5" />
      <path className="fill-white" d="M4.6 7h3.2l2.6 5.4L13 7h3.1l-4.2 8v3.2H8.9V15z" />
      <path className="fill-white" d="M16.9 7h2.8l-.6 6.6h-1.6z" />
      <circle className="fill-white" cx="18.2" cy="16.4" r="1.4" />
    </svg>
  );
}

export function ProviderMark({ provider }: { provider: IdentityProviderName }) {
  if (provider === "microsoft") return <MicrosoftMark />;
  if (provider === "yahoo") return <YahooMark />;
  return <GoogleMark />;
}
