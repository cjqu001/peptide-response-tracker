// demo_mock_api.js - In-browser stand-in for the Flask API in app.py.
// Used only by the static demo (docs/index.html). Data lives in memory and resets on reload.
(function () {
  const PALETTE = ["#2f6f8f", "#a63d40", "#5c7a51", "#8f6b3a", "#6b5b95", "#3a7d7c"];
  const pad = n => String(n).padStart(2, "0");
  const iso = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const today = () => iso(new Date());
  const daysAgo = n => { const d = new Date(); d.setDate(d.getDate() - n); return iso(d); };

  const db = { habits: [], logs: [], settings: {}, nextHabit: 1, nextLog: 1 };
  const EXAMPLE = [
    ["Water (example)", "glasses", 8, "number", [6,8,8,7,8,9,8,5,8,8,8,6,8,7]],
    ["Walk (example)", "min", 30, "number", [20,35,30,0,45,30,30,15,30,40,0,30,30,25]],
    ["Read (example)", "pages", 10, "number", [10,12,0,10,15,10,8,10,0,20,10,10,12,10]],
    ["Vitamin (example)", "dose", 1, "check", [1,1,1,0,1,1,1,1,1,0,1,1,1,1]],
    ["BPC-157 (example)", "mcg", 1, "measure", [250,250,250,250,250,null,null,250,250,250,250,250,null,null]],
    ["TB-500 (example)", "mg", 1, "measure", [2.5,null,null,2.5,null,null,null,2.5,null,null,2.5,null,null,null]],
    ["Sleep (example)", "hours", 1, "measure", [6.0,6.5,6.0,6.5,7.0,6.5,7.0,7.0,7.5,7.0,7.5,7.5,8.0,7.5]],
    ["Resting HR (example)", "bpm", 1, "measure", [66,65,66,64,63,64,62,62,61,60,61,59,59,58]],
    ["HRV (example)", "ms", 1, "measure", [41,43,42,45,46,44,48,49,50,52,51,54,55,56]],
    ["Energy 1-10 (example)", "score", 1, "measure", [5,5,6,5,6,6,7,6,7,7,8,7,8,8]],
    ["Pain 0-10 (example)", "score", 1, "measure", [6,6,5,6,5,5,4,4,4,3,3,3,2,2]],
  ];
  EXAMPLE.forEach(([name, unit, target, type, vals], k) => {
    const id = db.nextHabit++;
    db.habits.push({ id, name, unit, daily_target: target, color: PALETTE[k % PALETTE.length],
      input_type: type, profile: "PX", archived: 0, sort_order: id });
    vals.forEach((v, n) => {
      if (v === null) return;
      db.logs.push({ id: db.nextLog++, habit_id: id, log_date: daysAgo(vals.length - 1 - n), value: v, missed: v === 0 ? 1 : 0 });
    });
  });

  const json = (body, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  const visible = p => db.habits.filter(h => !h.archived && h.profile === p)
    .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
  const pub = h => ({ id: h.id, name: h.name, unit: h.unit, daily_target: h.daily_target, color: h.color, input_type: h.input_type });
  const logsOf = id => db.logs.filter(l => l.habit_id === id);
  const sum = a => a.reduce((s, x) => s + x, 0);
  const avg = a => a.length ? Math.round(sum(a) / a.length * 10) / 10 : null;
  const byDay = id => { const m = {}; logsOf(id).forEach(l => {
    const e = m[l.log_date] || (m[l.log_date] = { v: 0, m: 0 }); e.v += l.value; e.m = Math.max(e.m, l.missed); }); return m; };
  const nameTaken = (name, except) => db.habits.some(h => h.name === name && h.id !== except);

  function route(method, url, body) {
    const u = new URL(url, location.href);
    const path = u.pathname.replace(/^.*\/api\//, "/api/");
    const profile = u.searchParams.get("profile") || "CQ";
    let m;
    if (path === "/api/habits" && method === "GET") return json(visible(profile).map(pub));
    if (path === "/api/habits" && method === "POST") {
      const name = (body.name || "").trim();
      if (!name) return json({ error: "Name is required." }, 400);
      if (nameTaken(name)) return json({ error: "A habit with that name already exists." }, 409);
      const id = db.nextHabit++;
      db.habits.push({ id, name, unit: (body.unit || "count").trim(), daily_target: parseInt(body.daily_target || 1, 10),
        color: PALETTE[db.habits.length % PALETTE.length], profile: (body.profile || "CQ").trim(),
        input_type: ["check", "measure"].includes(body.input_type) ? body.input_type : "number",
        archived: 0, sort_order: Math.max(0, ...db.habits.map(h => h.sort_order)) + 1 });
      return json({ id }, 201);
    }
    if (path === "/api/habits/archived")
      return json(db.habits.filter(h => h.archived && h.profile === profile).map(h => ({ id: h.id, name: h.name })));
    if ((m = path.match(/^\/api\/habits\/(\d+)(?:\/(\w+))?$/))) {
      const id = +m[1], act = m[2], h = db.habits.find(x => x.id === id);
      if (!act && method === "DELETE") { if (h) h.archived = 1; return json({ ok: true }); }
      if (act === "unarchive") { if (h) h.archived = 0; return json({ ok: true }); }
      if (act === "delete") { db.habits = db.habits.filter(x => x.id !== id); db.logs = db.logs.filter(l => l.habit_id !== id); return json({ ok: true, deleted: id }); }
      if (act === "rename") {
        const name = (body.name || "").trim();
        if (!name) return json({ error: "Name is required." }, 400);
        if (nameTaken(name, id)) return json({ error: "A habit with that name already exists." }, 409);
        h.name = name; return json({ ok: true, name });
      }
      if (act === "move") {
        const rows = db.habits.filter(x => !x.archived).sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
        const i = rows.findIndex(x => x.id === id);
        if (i < 0) return json({ error: "Unknown habit." }, 404);
        const j = (body.direction || "").toLowerCase() === "up" ? i - 1 : i + 1;
        if (j < 0 || j >= rows.length) return json({ ok: true, moved: false });
        [rows[i].sort_order, rows[j].sort_order] = [rows[j].sort_order, rows[i].sort_order];
        return json({ ok: true, moved: true });
      }
    }
    if (path === "/api/log") {
      const hid = parseInt(body.habit_id, 10), value = parseInt(body.value || 0, 10), d = body.date || today();
      if (!value) return json({ error: "Value must be nonzero." }, 400);
      db.logs.push({ id: db.nextLog++, habit_id: hid, log_date: d, value, missed: 0 });
      return json({ date: d, day_total: sum(logsOf(hid).filter(l => l.log_date === d).map(l => l.value)) });
    }
    if (path === "/api/day") {
      const hid = parseInt(body.habit_id, 10), d = body.date || today();
      const fv = parseFloat(body.value || 0), value = Number.isInteger(fv) ? fv : Math.round(fv * 100) / 100;
      db.logs = db.logs.filter(l => !(l.habit_id === hid && l.log_date === d));
      let state = "blank";
      if (body.clear) state = "blank";
      else if (body.missed) { db.logs.push({ id: db.nextLog++, habit_id: hid, log_date: d, value: 0, missed: 1 }); state = "missed"; }
      else { db.logs.push({ id: db.nextLog++, habit_id: hid, log_date: d, value, missed: 0 }); state = "logged"; }
      return json({ date: d, day_total: value, state });
    }
    if ((m = path.match(/^\/api\/year\/(\d+)$/))) {
      const y = m[1], t = today(), wk = daysAgo(6), mon = t.slice(0, 7);
      return json({ year: +y, habits: visible(profile).map(h => {
        const days = byDay(h.id), daily = {}, missed = {};
        Object.entries(days).forEach(([d, e]) => { if (d.startsWith(y)) { daily[d] = e.v; if (e.m) missed[d] = true; } });
        const L = logsOf(h.id), s = f => sum(L.filter(f).map(l => l.value));
        return { ...pub(h), daily, missed, totals: { today: s(l => l.log_date === t), week: s(l => l.log_date >= wk),
          month: s(l => l.log_date.startsWith(mon)), year: s(l => l.log_date.startsWith(y)) } };
      }) });
    }
    if (path === "/api/stats") {
      const t = today(), d7 = daysAgo(6), d30 = daysAgo(29), yr = t.slice(0, 4), out = {};
      visible(profile).forEach(h => {
        const L = logsOf(h.id);
        if (h.input_type === "measure") {
          const v = f => avg(L.filter(l => !l.missed && f(l)).map(l => l.value));
          out[h.id] = { today: v(l => l.log_date === t), d7: v(l => l.log_date >= d7), d30: v(l => l.log_date >= d30),
            year: v(l => l.log_date.startsWith(yr)), lifetime: v(() => true), streak: 0 };
          return;
        }
        const s = f => sum(L.filter(f).map(l => l.value));
        const days = Object.entries(byDay(h.id)).filter(([, e]) => e.v > 0).map(([d]) => d).sort();
        let longest = 0, run = 0, prev = null;
        days.forEach(ds => { const d = new Date(ds + "T00:00:00");
          run = prev && Math.round((d - prev) / 864e5) === 1 ? run + 1 : 1; longest = Math.max(longest, run); prev = d; });
        out[h.id] = { today: s(l => l.log_date === t), d7: s(l => l.log_date >= d7), d30: s(l => l.log_date >= d30),
          year: s(l => l.log_date.startsWith(yr)), lifetime: s(() => true), streak: longest };
      });
      return json({ profile, year: +t.slice(0, 4), stats: out });
    }
    if (path === "/api/settings" && method === "GET") return json({ ...(db.settings[profile] || {}) });
    if (path === "/api/settings" && method === "POST") {
      const p = (body.profile || "CQ").trim(), s = db.settings[p] || (db.settings[p] = {});
      ["height_in", "weight_habit_id", "display_name"].forEach(k => {
        if (k in body) s[k] = body[k] === null || body[k] === "" ? null : String(body[k]); });
      return json({ ok: true });
    }
    if (path === "/api/profile-names") {
      const out = {}; Object.entries(db.settings).forEach(([p, s]) => { if (s.display_name) out[p] = s.display_name; });
      return json(out);
    }
    return json({ error: "Not available in the demo." }, 404);
  }

  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = typeof input === "string" ? input : input.url;
    if (!/\/api\//.test(url)) return realFetch(input, init);
    let body = {}; try { body = init.body ? JSON.parse(init.body) : {}; } catch (e) {}
    return route((init.method || "GET").toUpperCase(), url, body);
  };

  // CSV export without a server: build the same layout as /api/export/csv and download it.
  window.demoExportCsv = function (profile) {
    const hs = visible(profile), by = {};
    hs.forEach(h => Object.entries(byDay(h.id)).forEach(([d, e]) => {
      if (e.m && !e.v) return; (by[d] || (by[d] = {}))[h.id] = e.v; }));
    const q = s => /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    const rows = [["Date", ...hs.map(h => `${h.name} (${h.unit})`)].map(q).join(",")];
    Object.keys(by).sort().forEach(d => rows.push([d, ...hs.map(h => by[d][h.id] ?? "")].join(",")));
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + rows.join("\r\n") + "\r\n"], { type: "text/csv" }));
    a.download = `habit_tracker_${profile}_${today().replace(/-/g, "")}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
  };

  // Open on the Example profile the first time someone visits the demo.
  try { if (!localStorage.getItem("ht_profile")) localStorage.setItem("ht_profile", "PX"); } catch (e) {}
})();
