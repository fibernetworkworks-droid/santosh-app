/* v0.435 PARIVAAR: the business's web admin, made by Hoola App Sahayak.
   Signs in with an app staff / admin account and talks ONLY to /api/app-api/<app_key>/... - every rule (who may see,
   change, assign, export) is checked by the server. Data is written with textContent only, never as HTML. */
(function () {
  "use strict";
  var KEY = (location.pathname.match(/\/app-admin\/(ak[0-9a-f]{8,38})/) || [])[1] || "";
  var API = "/api/app-api/" + KEY;
  var TK = "hoola_admin_" + KEY;
  var S = { token: "", ov: null, view: "dash", list: null, rows: [], offset: 0, q: "", status: "", team: null };
  var app = document.getElementById("app");

  function store(k, v) { try { if (v === undefined) return sessionStorage.getItem(k) || ""; if (v) sessionStorage.setItem(k, v); else sessionStorage.removeItem(k); } catch (e) { return ""; } return ""; }

  function h(tag, attrs) {
    var el = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "text") el.textContent = String(v);
      else if (k === "on") Object.keys(v).forEach(function (e) { el.addEventListener(e, v[e]); });
      else if (k === "cls") el.className = v;
      else el.setAttribute(k, v === true ? "" : String(v));
    });
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c === null || c === undefined || c === false) continue;
      if (Array.isArray(c)) c.forEach(function (x) { if (x) el.appendChild(typeof x === "string" ? document.createTextNode(x) : x); });
      else el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return el;
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function toast(t) { var x = h("div", { cls: "toast", text: t, role: "status" }); document.body.appendChild(x); setTimeout(function () { x.remove(); }, 2600); }

  function call(method, path, body) {
    var o = { method: method, headers: { "Accept": "application/json" } };
    if (S.token) o.headers["Authorization"] = "Bearer " + S.token;
    if (body !== undefined) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(body); }
    return fetch(API + path, o).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) { var e = new Error(j.error || ("Error " + r.status)); e.code = r.status; throw e; }
        return j;
      });
    }, function () { var e = new Error("No internet. Please try again."); e.code = 0; throw e; });
  }
  function fail(e) {
    if (e && e.code === 401) { signOut(); return; }
    toast((e && e.message) || "Something went wrong.");
  }

  // ------------------------------------------------------------ sign in
  function loginView(msg) {
    var email = h("input", { type: "email", autocomplete: "username", required: true, id: "em" });
    var pw = h("input", { type: "password", autocomplete: "current-password", required: true, id: "pw" });
    var err = h("div", { cls: "err", role: "alert", text: msg || "" });
    var btn = h("button", { cls: "btn pri", type: "submit", text: "Sign in" });
    var form = h("form", { cls: "login", on: { submit: function (ev) {
      ev.preventDefault();
      btn.disabled = true; err.textContent = "";
      call("POST", "/login", { email: email.value, password: pw.value }).then(function (j) {
        S.token = j.token || ""; store(TK, S.token); boot();
      }).catch(function (e) { err.textContent = e.message; btn.disabled = false; });
    } } },
      h("h1", { text: "Business admin" }),
      h("p", { text: "Sign in with your staff or admin account of this app." }),
      h("div", { cls: "f" }, h("label", { "for": "em", text: "Email" }), email),
      h("div", { cls: "f" }, h("label", { "for": "pw", text: "Password" }), pw),
      err, btn,
      h("p", { cls: "note", text: "New staff accounts see nothing until the owner or an admin makes them staff." }));
    clear(app).appendChild(form);
    email.focus();
  }
  function signOut() {
    var t = S.token;
    S.token = ""; store(TK, "");
    if (t) fetch(API + "/logout", { method: "POST", headers: { "Authorization": "Bearer " + t } }).catch(function () {});
    loginView("");
  }

  // ------------------------------------------------------------ shell
  function boot() {
    if (!KEY) { clear(app).appendChild(h("div", { cls: "boot", text: "This address is not a business admin." })); return; }
    S.token = S.token || store(TK);
    if (!S.token) { loginView(""); return; }
    call("GET", "/admin/overview").then(function (ov) { S.ov = ov; render(); }).catch(function (e) {
      if (e.code === 401) { S.token = ""; store(TK, ""); loginView(""); }
      else if (e.code === 403) { S.token = ""; store(TK, ""); loginView(e.message + " Ask the owner to make this account staff."); }
      else loginView(e.message);
    });
  }

  function nav(view, list) {
    S.view = view; S.list = list || null; S.rows = []; S.offset = 0; S.q = ""; S.status = "";
    var side = document.querySelector(".side"); if (side) side.classList.remove("open");
    render();
  }

  function render() {
    var ov = S.ov;
    var side = h("nav", { cls: "side", "aria-label": "Admin" },
      h("div", { cls: "name", text: ov.name || "Business" }),
      link("Dashboard", "dash"),
      h("div", { cls: "grp", text: "Lists" }),
      ov.lists.map(function (l) { return link(l.label, "list", l, ov.counts && ov.counts[l.key]); }),
      h("div", { cls: "grp", text: "People" }),
      link("Partners", "partners", null, ov.waiting ? ov.waiting + " waiting" : ""),
      link("Team", "team"),
      ov.faces && ov.faces.length > 1 ? link("Apps", "apps") : null,
      h("div", { cls: "me" }, h("div", { text: (ov.me && (ov.me.name || ov.me.email)) || "" }),
        h("div", { text: ov.admin ? "Admin" : "Staff" }),
        h("button", { cls: "btn", type: "button", text: "Sign out", on: { click: signOut }, style: "margin-top:8px" })));
    var main = h("main", { cls: "main" },
      h("button", { cls: "btn menu-btn", type: "button", text: "Menu", on: { click: function () { side.classList.toggle("open"); } } }));
    clear(app).appendChild(h("div", { cls: "shell" }, side, main));
    if (S.view === "dash") dash(main);
    else if (S.view === "list") listView(main);
    else if (S.view === "partners") partnersView(main);
    else if (S.view === "team") teamView(main);
    else if (S.view === "apps") appsView(main);
  }
  function link(text, view, list, count) {
    var on = S.view === view && (!list || (S.list && S.list.key === list.key));
    return h("a", { cls: on ? "on" : "", href: "#", "aria-current": on ? "page" : null,
      on: { click: function (e) { e.preventDefault(); nav(view, list); } } },
      h("span", { text: text }), count !== undefined && count !== "" && count !== null ? h("span", { cls: "cnt", text: String(count) }) : null);
  }

  // ------------------------------------------------------------ dashboard
  function money(n) { return "Rs " + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 }); }
  function dash(main) {
    main.appendChild(h("h2", { text: "Dashboard" }));
    var box = h("div", { cls: "note", text: "Loading…" });
    main.appendChild(box);
    call("GET", "/stats?days=14").then(function (st) {
      clear(box).className = "";
      var cards = h("div", { cls: "cards" });
      st.lists.forEach(function (l) {
        var max = Math.max.apply(null, l.daily.concat([1]));
        cards.appendChild(h("div", { cls: "card" },
          h("div", { cls: "k", text: l.label }),
          h("div", { cls: "v", text: String(l.count) }),
          l.total !== null && l.total !== undefined ? h("div", { cls: "note", text: money(l.total) + " total" }) : null,
          l.rating ? h("div", { cls: "note", text: l.rating.avg + " stars (" + l.rating.count + ")" }) : null,
          h("div", { cls: "spark", "aria-label": "Last 14 days" }, l.daily.map(function (n) { return h("i", { style: "height:" + Math.round(100 * n / max) + "%", title: String(n) }); })),
          h("div", { cls: "chips" }, Object.keys(l.status || {}).map(function (k) { return h("span", { cls: "chip", text: k + " " + l.status[k] }); }))));
      });
      box.appendChild(cards);
      if (st.unassigned) box.appendChild(h("p", { text: st.unassigned + " open rows are with nobody yet." }));
      if (st.team && st.team.length) {
        box.appendChild(h("h2", { text: "Team load" }));
        box.appendChild(table(["Name", "Open work", "Rating"], st.team.map(function (p) { return [p.name, String(p.open), p.rating ? p.rating + " (" + p.rated + ")" : "-"]; })));
      }
    }).catch(function (e) { box.textContent = e.message; });
  }

  function table(head, rows, onRow) {
    var tb = h("tbody");
    rows.forEach(function (r, i) {
      var tr = h("tr", onRow ? { tabindex: "0", on: { click: function () { onRow(i); }, keydown: function (e) { if (e.key === "Enter") onRow(i); } } } : {});
      r.forEach(function (c) { tr.appendChild(typeof c === "object" && c ? h("td", {}, c) : h("td", { text: c === undefined || c === null ? "" : String(c), title: c === undefined || c === null ? "" : String(c) })); });
      tb.appendChild(tr);
    });
    return h("div", { cls: "tw" }, h("table", {}, h("thead", {}, h("tr", {}, head.map(function (x) { return h("th", { text: x }); }))), tb));
  }

  // ------------------------------------------------------------ a list
  function show(v) {
    if (v === true) return "Yes";
    if (v === false) return "No";
    if (v === null || v === undefined) return "";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }
  function pill(s) {
    var low = String(s || "").toLowerCase();
    var k = /deliver|done|complet|paid|confirm|verified/.test(low) ? "good" : /cancel|reject|fail|expired/.test(low) ? "bad" : "";
    return s ? h("span", { cls: "pill " + k, text: s }) : "";
  }
  function listView(main) {
    var l = S.list;
    var fields = l.fields.filter(function (f) { return f.key !== "status"; });
    var cols = fields.slice(0, 5);
    var search = h("input", { type: "search", placeholder: "Search " + l.label, "aria-label": "Search", value: S.q });
    var st = h("select", { "aria-label": "Status" }, h("option", { value: "", text: "Every status" }),
      (l.statuses || []).map(function (s) { var o = h("option", { value: s, text: s }); if (s === S.status) o.selected = true; return o; }));
    var exp = h("button", { cls: "btn", type: "button", text: "Export CSV", on: { click: function () { exportCsv(l); } } });
    var t;
    search.addEventListener("input", function () { clearTimeout(t); t = setTimeout(function () { S.q = search.value; S.offset = 0; S.rows = []; load(); }, 300); });
    st.addEventListener("change", function () { S.status = st.value; S.offset = 0; S.rows = []; load(); });
    main.appendChild(h("h2", { text: l.label }));
    main.appendChild(h("div", { cls: "bar" }, search, l.statuses && l.statuses.length ? st : null, exp));
    var box = h("div");
    main.appendChild(box);
    function draw(more) {
      clear(box);
      if (!S.rows.length) { box.appendChild(h("p", { cls: "note", text: "Nothing here yet." })); return; }
      var head = cols.map(function (f) { return f.label; });
      if (l.statuses && l.statuses.length) head.push("Status");
      head.push("With", "Added");
      box.appendChild(table(head, S.rows.map(function (r) {
        var row = cols.map(function (f) { return show(r[f.key]); });
        if (l.statuses && l.statuses.length) row.push(pill(r.status));
        row.push(r.assigned_name || "", (r.created || "").slice(0, 16).replace("T", " "));
        return row;
      }), function (i) { open(l, S.rows[i]); }));
      if (more) box.appendChild(h("button", { cls: "btn more", type: "button", text: "Load more", on: { click: function () { S.offset += 50; load(); } } }));
    }
    function load() {
      var qs = "?limit=50&offset=" + S.offset + (S.q ? "&q=" + encodeURIComponent(S.q) : "") + (S.status ? "&status=" + encodeURIComponent(S.status) : "");
      call("GET", "/c/" + encodeURIComponent(l.key) + qs).then(function (j) {
        S.rows = S.offset ? S.rows.concat(j.rows) : j.rows;
        draw(j.rows.length === 50);
      }).catch(fail);
    }
    load();
  }

  function input(f, v) {
    var id = "f_" + f.key;
    var el;
    if (f.type === "long_text" || f.type === "richtext") el = h("textarea", { id: id });
    else if (f.type === "choice") {
      el = h("select", { id: id }, h("option", { value: "", text: "-" }), (f.options || []).map(function (o) { return h("option", { value: o, text: o }); }));
    } else if (f.type === "yes_no") el = h("input", { id: id, type: "checkbox" });
    else if (f.type === "number") el = h("input", { id: id, type: "number", step: "any" });
    else if (f.type === "date") el = h("input", { id: id, type: "date" });
    else if (["photo", "photos", "signature", "video", "audio", "file", "ref", "location", "scan"].indexOf(f.type) >= 0) return null;
    else el = h("input", { id: id, type: f.type === "email" ? "email" : f.type === "phone" ? "tel" : "text" });
    if (f.type === "yes_no") el.checked = !!v; else el.value = v === undefined || v === null ? "" : String(v);
    el.dataset.key = f.key; el.dataset.type = f.type;
    return h("div", { cls: "f" }, h("label", { "for": id, text: f.label + (f.admin_only ? " (staff only)" : "") }), el);
  }

  function open(l, r) {
    var old = document.querySelector(".drawer"); if (old) old.remove();
    var form = h("div");
    var ro = [];
    l.fields.forEach(function (f) {
      var box = input(f, r[f.key]);
      if (box) form.appendChild(box); else if (r[f.key] !== undefined && r[f.key] !== "") ro.push([f.label, show(r[f.key])]);
    });
    ["items", "total", "discount", "delivery_fee", "assigned_name", "rating", "rating_note", "created"].forEach(function (k) {
      if (r[k] !== undefined && r[k] !== "" && r[k] !== null && !l.fields.some(function (f) { return f.key === k; })) ro.push([k.replace(/_/g, " "), show(r[k])]);
    });
    var kv = h("div", { cls: "kv" });
    ro.forEach(function (p) { kv.appendChild(h("div", { text: p[0] })); kv.appendChild(h("div", { text: p[1], style: "white-space:pre-wrap" })); });
    var err = h("div", { cls: "err", role: "alert" });
    var save = h("button", { cls: "btn pri", type: "button", text: "Save" });
    var close = h("button", { cls: "btn", type: "button", text: "Close" });
    var assign = h("select", { "aria-label": "Give to" }, h("option", { value: "", text: "With nobody" }));
    var dr = h("aside", { cls: "drawer", role: "dialog", "aria-label": l.label },
      h("h3", { text: l.label + " " + String(r.id || "").slice(-6).toUpperCase() }), kv, form,
      h("div", { cls: "f" }, h("label", { text: "Given to" }), assign), err,
      h("div", { cls: "acts" }, save, close));
    document.body.appendChild(dr);
    close.addEventListener("click", function () { dr.remove(); });
    dr.addEventListener("keydown", function (e) { if (e.key === "Escape") dr.remove(); });
    (S.team ? Promise.resolve(S.team) : call("GET", "/team").then(function (t) { S.team = t; return t; })).then(function (t) {
      t.team.forEach(function (p) { var o = h("option", { value: p.id, text: p.name + " (" + p.open + " open)" }); if (p.id === r.assigned_to) o.selected = true; assign.appendChild(o); });
      if (!t.admin) { assign.disabled = true; assign.title = "Only an admin gives work to others."; }
    }).catch(function () { assign.disabled = true; });
    save.addEventListener("click", function () {
      var body = {};
      form.querySelectorAll("[data-key]").forEach(function (el) {
        var k = el.dataset.key;
        var v = el.dataset.type === "yes_no" ? el.checked : el.value;
        if (show(v) !== show(r[k] === undefined ? (el.dataset.type === "yes_no" ? false : "") : r[k])) body[k] = v;
      });
      if (!assign.disabled && assign.value !== (r.assigned_to || "")) body._assign = assign.value;
      if (!Object.keys(body).length) { dr.remove(); return; }
      save.disabled = true; err.textContent = "";
      call("PATCH", "/c/" + encodeURIComponent(l.key) + "/" + encodeURIComponent(r.id), body).then(function (x) {
        Object.assign(r, x); toast("Saved"); dr.remove(); render();
      }).catch(function (e) { err.textContent = e.message; save.disabled = false; });
    });
  }

  function exportCsv(l) {
    fetch(API + "/admin/export/" + encodeURIComponent(l.key), { headers: { "Authorization": "Bearer " + S.token } }).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.error || "Export failed"); });
      return r.blob();
    }).then(function (b) {
      var a = h("a", { href: URL.createObjectURL(b), download: l.key + ".csv" });
      document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    }).catch(fail);
  }

  // ------------------------------------------------------------ partners (delivery partners / partner shops)
  function partnersView(main) {
    main.appendChild(h("h2", { text: "Partners" }));
    var box = h("div", { cls: "note", text: "Loading…" });
    main.appendChild(box);
    call("GET", "/admin/partners").then(function (j) {
      clear(box).className = "";
      if (!j.partners.length) { box.appendChild(h("p", { cls: "note", text: "No partner has applied yet. Riders and partner shops apply from their own app." })); return; }
      box.appendChild(table(["Name", "Email", "Kind", "State", "Shop", ""], j.partners.map(function (p) {
        var acts = h("div", { style: "display:flex;gap:6px" });
        if (j.admin) {
          if (p.state === "waiting" || p.state === "refused" || p.state === "removed") {
            var shop = null;
            if (p.kind === "vendor") {
              shop = h("select", { "aria-label": "Which shop" }, h("option", { value: "", text: "Which shop?" }),
                j.shops.map(function (s) { return h("option", { value: s.id, text: s.name }); }));
              acts.appendChild(shop);
            }
            acts.appendChild(h("button", { cls: "btn pri", type: "button", text: "Approve", on: { click: function () {
              decide(p.id, { action: "approve", link_row: shop ? shop.value : "" });
            } } }));
          }
          if (p.state === "waiting") acts.appendChild(h("button", { cls: "btn", type: "button", text: "Refuse", on: { click: function () { decide(p.id, { action: "refuse" }); } } }));
          if (p.state === "approved") acts.appendChild(h("button", { cls: "btn bad", type: "button", text: "Remove", on: { click: function () {
            if (confirm("Remove " + p.name + "? Their open jobs go back to the pool and they are signed out.")) decide(p.id, { action: "remove" });
          } } }));
        }
        return [p.name, p.email, p.label, pill(p.state === "approved" ? "Approved" : p.state === "waiting" ? "Waiting" : p.state === "refused" ? "Refused" : "Removed"), p.link_name || "", acts];
      })));
      if (!j.admin) box.appendChild(h("p", { cls: "note", text: "Only an admin approves partners." }));
    }).catch(function (e) { box.textContent = e.message; });
  }
  function decide(pid, body) {
    call("POST", "/admin/partners/" + encodeURIComponent(pid), body).then(function () {
      toast("Done"); return call("GET", "/admin/overview");
    }).then(function (ov) { S.ov = ov; render(); }).catch(fail);
  }

  // ------------------------------------------------------------ team (accounts and roles)
  function teamView(main) {
    main.appendChild(h("h2", { text: "Team" }));
    var box = h("div", { cls: "note", text: "Loading…" });
    main.appendChild(box);
    call("GET", "/admin/members").then(function (j) {
      clear(box).className = "";
      box.appendChild(table(["Name", "Email", "Role", "Since"], j.members.map(function (m) {
        var role = m.role;
        if (S.ov.admin && (m.role === "member" || m.role === "staff") && !(S.ov.me && S.ov.me.id === m.id)) {
          role = h("select", { "aria-label": "Role", on: { change: function (e) {
            call("POST", "/admin/members/" + encodeURIComponent(m.id) + "/role", { role: e.target.value }).then(function () { toast("Role changed"); }).catch(fail);
          } } }, ["member", "staff"].map(function (x) { var o = h("option", { value: x, text: x }); if (x === m.role) o.selected = true; return o; }));
        }
        return [m.name, m.email, role, (m.since || "").slice(0, 10)];
      })));
      box.appendChild(h("p", { cls: "note", text: "Admins are made by the owner from Hoola. Partners are managed under Partners." }));
    }).catch(function (e) { box.textContent = e.message; });
  }

  function appsView(main) {
    main.appendChild(h("h2", { text: "Apps on this business" }));
    main.appendChild(table(["App", "Kind", "Status"], S.ov.faces.map(function (f) {
      return [(f.name || "") + " (" + (f.number || "") + ")", f.kind === "main" ? "Main app" : (f.label || f.kind), f.status || ""];
    })));
    main.appendChild(h("p", { cls: "note", text: "Every app here uses the same accounts and data." }));
  }

  boot();
})();
