# 0001 Stack and the legacy application

Context: the first Bodha was a React/Vite frontend, an Express backend and a Node AI service on
MongoDB. The owner asked for Next.js, Tailwind CSS and TypeScript with a Python backend and Gemini.

Choice: Next.js App Router frontend; FastAPI, SQLAlchemy and Alembic on Postgres; S3-compatible
object storage. This matches ChartMate's stack, so its code sets and flows port directly. The old
application stays on disk in `legacy/` and is never committed.

Follows: no data migration from MongoDB is written; a practice moving from the legacy app
re-uploads its open notes.
