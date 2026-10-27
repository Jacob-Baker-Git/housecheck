# MEMORY.md: HouseCheck working notes (Open Agent Hackathon 2026)

**Deadline: Tue 27 Oct, 23:45. Target submit 20:00.** Solo build (Jacob). Submit: public GitHub repo, 1–4 min video, slide deck, sponsor-tech write-up.

## Zetaris criteria (from "Build with Zetaris evaluation criteria" PDF)
1a use case + 3+ sources → docs/usl/USE_CASE.md ✅ drafted
1b onboard + 2–3 queries per source → sql/01, sql/02 ✅ live run 27 Oct (docs/usl/RESULTS.md)
1c USL + DDL, 2–3 queries showing it active, 1 DQ rule executed → sql/04, sql/05 ✅ 67/67, 5 DQ rules, 70 invalid FSA dates caught
2a time saved vs hand-coded (+bonus hand-coded part) → docs/usl/REFLECTION.md ✅ real numbers (USL 2,148 ms vs hand-coded 547 ms, reported honestly)
2b would it help my work (+forecast) → REFLECTION.md ⏳ needs Jacob's two estimates
2c PM requirement (+mock feature/USL) → REFLECTION.md ✅ drafted (parameterised REST sources)

## Status (27 Oct 07:20)
- Done: doctor all PASS; USL clean; live compare GU2 7XH vs SO14 5FN works (Nemotron via Nightshift, ~30–190 s); repo public at https://github.com/Jacob-Baker-Git/housecheck
- Next: web page check (`housecheck serve`), 2b estimates, slide deck, demo video (1–4 min), submit on HackOS.
- Push changes: `git add -A && git commit -qm "msg" && git push`

## Known unknowns
- Zetaris REST: `POST {ZETARIS_REST_URL}/sql-editor/sqls/run`, Bearer key, X-Org-ID, port 8888 `/api/v1.0` (copied from other teams' repos).
- USL syntax copied from a team whose run passed: COMPILE USL ... DEPLOY NAMESPACE ... DDL, ACTIVATE USL TABLE, REGISTER DQ, RUN DQ TABLE. Column named `text` is rejected.
- Nightshift: WSL reaches it via `netsh interface portproxy` on 172.21.128.1:8088 (mirrored mode didn't take). METERLESS_BASE_URL in .env points there. If the IP changes after a reboot, redo the portproxy.
- No Cursor: built with Claude as coding assistant; disclosed in README.

## Machine notes
- Zetaris in WSL Ubuntu on D:, `~/zetaris-platform`. Stop/start: `docker compose stop` / `start`. **Never `down -v`.**
