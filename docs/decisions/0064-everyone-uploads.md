# 0064 Everyone in a practice can upload, and the drop area is always in view

Date: 2026-11-28

Context: only admins and coders could upload. In many practices billers, CDI staff or front-desk viewers
are the ones who send the day's notes. The empty queue gave no way to add notes, and once files were on
the Upload screen the only way to add more was a small button in the table header.

## Choice

- Upload, page-one preview and upload history are open to every practice role (`UPLOADERS =
  PRACTICE_ROLES`, and the `upload` area in `lib/roles.ts`). History shows provider, date, place, visit
  type, uploader and counts, never patient details, so a viewer who cannot open notes sees nothing new.
- Replacing a note's PDF, voiding, changing the visit type and retrying a read stay with admins and coders,
  now named `NOTE_KEEPERS` in both the API and the client, so widening upload widened nothing else.
- The Upload screen opens on a large dashed drop area with an upload mark, "Drop PDF notes here" and a
  primary Choose files button. On touch screens, where nothing can be dragged, the drop line is hidden and
  the button remains. Once files are added, a compact drop strip with Add files sits below the table.
- An empty queue offers Upload notes to anyone who can upload.
