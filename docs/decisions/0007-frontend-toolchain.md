# 0007 Frontend toolchain versions

Context: the owner asked for the latest stable version of every dependency.

Choice: Next.js 16, React 19, Tailwind CSS 4 (CSS-first tokens in `globals.css`), Vitest 5 with
jsdom, ESLint 10 with `eslint-config-next`. TypeScript stays on 6.0: TypeScript 7 ships no
JavaScript compiler API, which Next.js's build-time type check and typescript-eslint need.

Follows: move to TypeScript 7 when Next.js and typescript-eslint support it. Node 22.22.2 or
24.15.0 and later, which jsdom 31 requires.
