from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template_string, request, url_for

APP_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("ADMISSIONS_DB", APP_DIR / "admissions.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-dev-key-change-before-deploy")

KINDS = {"招生文案": "招生文案", "社群貼文": "社群貼文", "電子郵件": "電子郵件"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 category TEXT NOT NULL DEFAULT '',
 audience TEXT NOT NULL DEFAULT '',
 start_date TEXT NOT NULL DEFAULT '',
 deleted_at TEXT,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS copies (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
 kind TEXT NOT NULL,
 title TEXT NOT NULL,
 body TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL
);
"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def initialize():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    course_columns = {row[1] for row in conn.execute("PRAGMA table_info(courses)")}
    if "deleted_at" not in course_columns:
        conn.execute("ALTER TABLE courses ADD COLUMN deleted_at TEXT")
    conn.commit()
    conn.close()

# Also initialize when the app is imported by a production WSGI server (for example, Gunicorn).
initialize()

BASE = r'''
<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}｜招生文案工作室</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--ink:#202b25;--muted:#77817a;--line:#e7e9e5;--paper:#fbfaf7;--green:#285d45;--pale:#eaf1e8;--orange:#dd8a5c;--shadow:0 12px 35px #2031270a}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:'DM Sans','Noto Sans TC',sans-serif;font-size:14px}a{color:inherit;text-decoration:none}button,input,textarea,select{font:inherit}.shell{display:grid;grid-template-columns:246px minmax(0,1fr);min-height:100vh}.sidebar{background:#f3f3ed;border-right:1px solid var(--line);padding:27px 17px;display:flex;flex-direction:column}.brand{display:flex;gap:11px;align-items:center;padding:2px 10px 34px}.brandmark{height:35px;width:35px;background:var(--green);border-radius:11px;color:white;display:grid;place-items:center;font-size:19px}.brand strong{display:block;font-size:14px;letter-spacing:.02em}.brand small{color:var(--muted);font-size:11px}.navlabel{font-size:10px;text-transform:uppercase;letter-spacing:.14em;color:#9a9f98;padding:0 11px;margin:4px 0 9px}.nav{display:flex;align-items:center;gap:11px;padding:11px;border-radius:9px;color:#657068;margin:2px 0}.nav.active{background:#e5ece3;color:var(--green);font-weight:700}.navicon{width:19px;text-align:center;font-size:15px}.sidefoot{margin-top:auto;border-top:1px solid var(--line);padding:15px 10px 0;color:var(--muted);font-size:11px;line-height:1.7}.sidefoot b{color:var(--ink);display:block;font-size:12px}.main{padding:31px clamp(22px,5vw,68px) 52px;max-width:1440px;width:100%;margin:0 auto}.topline{display:flex;justify-content:space-between;align-items:center;margin-bottom:35px}.crumb{font-size:12px;color:var(--muted)}.crumb span{color:#bec3bd;margin:0 8px}.user{display:flex;gap:10px;align-items:center;font-size:12px}.avatar{width:30px;height:30px;border-radius:50%;background:#e8d2bd;color:#714d31;display:grid;place-items:center;font-weight:700}.heading{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:25px}.eyebrow{color:var(--green);font-size:11px;letter-spacing:.1em;font-weight:700;margin-bottom:9px}.heading h1{font-size:clamp(25px,3vw,34px);letter-spacing:-.04em;margin:0 0 8px}.heading p{margin:0;color:var(--muted);font-size:13px}.btn{border:1px solid var(--line);border-radius:8px;padding:10px 15px;background:white;cursor:pointer;color:var(--ink);display:inline-flex;align-items:center;gap:7px;font-weight:600;font-size:12px}.btn.primary{color:white;background:var(--green);border-color:var(--green)}.btn:hover{filter:brightness(.97)}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:25px}.stat{background:white;border:1px solid var(--line);border-radius:11px;padding:17px 19px;box-shadow:var(--shadow)}.statlabel{color:var(--muted);font-size:11px;display:flex;justify-content:space-between}.statval{font-size:26px;font-weight:700;margin-top:9px;letter-spacing:-.04em}.statnote{font-size:10px;color:#9ca49c;margin-top:3px}.statdot{width:7px;height:7px;background:#77a782;border-radius:50%;display:inline-block;margin-right:5px}.toolbar{display:flex;justify-content:space-between;gap:12px;margin:0 0 13px}.search{position:relative;flex:1;max-width:390px}.search input{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff;padding:10px 13px 10px 36px;outline:none}.search:before{content:'⌕';position:absolute;left:13px;top:7px;font-size:19px;color:#879089}.select{background:#fff;border:1px solid var(--line);border-radius:8px;padding:9px 12px;color:#69736c}.tablewrap{background:white;border:1px solid var(--line);border-radius:11px;overflow:hidden;box-shadow:var(--shadow)}table{width:100%;border-collapse:collapse;text-align:left}th{font-size:10px;letter-spacing:.09em;color:#919992;font-weight:600;background:#fcfcfa;padding:13px 17px;border-bottom:1px solid var(--line)}td{padding:15px 17px;border-bottom:1px solid #eff0ed;vertical-align:middle}tr:last-child td{border:0}.coursename{font-weight:700;font-size:13px}.subtext{font-size:11px;color:var(--muted);margin-top:4px}.tag{display:inline-block;background:#eff3ed;color:#4d7457;border-radius:20px;padding:4px 9px;font-size:10px}.chips{display:flex;gap:5px;flex-wrap:wrap}.chip{border:1px solid var(--line);border-radius:5px;padding:4px 7px;color:#69736c;font-size:10px}.chip.missing{color:#a5aaa4;background:#fafaf8}.actions{display:flex;gap:6px;justify-content:flex-end}.iconbtn{border:1px solid var(--line);background:white;border-radius:6px;width:29px;height:29px;display:grid;place-items:center;color:#69736c;cursor:pointer}.empty{text-align:center;padding:50px 20px;color:var(--muted)}.empty b{display:block;color:var(--ink);font-size:15px;margin-bottom:6px}.flash{padding:11px 14px;border-radius:8px;background:#e8f1e7;color:#315f3e;margin-bottom:16px;font-size:12px}.formcard,.detailcard{border:1px solid var(--line);background:white;border-radius:11px;padding:23px;box-shadow:var(--shadow);max-width:820px}.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:17px}.field{display:flex;flex-direction:column;gap:7px}.field.full{grid-column:1/-1}.field label{font-size:11px;font-weight:700;color:#626d65}.field input,.field textarea,.field select{border:1px solid var(--line);border-radius:7px;padding:10px 11px;background:#fff;outline-color:#8cab91}.field textarea{min-height:160px;resize:vertical;line-height:1.7}.field textarea.short{min-height:100px}.formactions{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--line);margin-top:20px;padding-top:17px}.muted{color:var(--muted);font-size:11px}.detailhead{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;padding-bottom:19px;border-bottom:1px solid var(--line)}.detailhead h2{margin:0;font-size:21px}.detailhead p{color:var(--muted);font-size:12px;margin:7px 0}.copy{padding:19px 0;border-bottom:1px solid var(--line)}.copy:last-child{border-bottom:0;padding-bottom:0}.copytop{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.copytop h3{font-size:13px;margin:0}.copybody{white-space:pre-wrap;line-height:1.85;font-size:13px;color:#515d55;background:#fbfbf9;padding:15px;border-radius:7px}.notice{padding:13px;color:var(--muted);font-size:12px}@media(max-width:850px){.shell{grid-template-columns:1fr}.sidebar{display:none}.main{padding:22px 16px 38px}.stats{gap:8px}.stat{padding:13px}.tablewrap{overflow:auto}table{min-width:680px}}@media(max-width:540px){.heading{align-items:flex-start;flex-direction:column}.stats{grid-template-columns:1fr}.stat{display:flex;align-items:center;justify-content:space-between}.statval{margin:0}.formgrid{grid-template-columns:1fr}.field.full{grid-column:auto}.topline{margin-bottom:24px}}
</style></head><body><div class="shell"><aside class="sidebar"><a class="brand" href="{{ url_for('index') }}"><span class="brandmark">✳</span><span><strong>招生文案工作室</strong><small>ADMISSIONS STUDIO</small></span></a><div class="navlabel">工作空間</div><a class="nav {% if title=='文案總覽' %}active{% endif %}" href="{{ url_for('index') }}"><span class="navicon">▦</span>文案總覽</a><a class="nav" href="{{ url_for('index') }}#courses"><span class="navicon">◫</span>課程資料</a><a class="nav {% if title=='垃圾桶' %}active{% endif %}" href="{{ url_for('trash') }}"><span class="navicon">▤</span>垃圾桶</a><div class="sidefoot"><b>讓每個好課程被看見</b>集中管理內容，讓招生溝通更有一致性。</div></aside><main class="main"><div class="topline"><div class="crumb">工作空間 <span>/</span> {{ title }}</div><div class="user"><span>招生企劃</span><span class="avatar">招</span></div></div>{% with messages = get_flashed_messages() %}{% if messages %}<div class="flash">{{ messages[0] }}</div>{% endif %}{% endwith %}{{ content|safe }}</main></div></body></html>
'''

def page(title, content, **context):
    return render_template_string(BASE, title=title, content=render_template_string(content, **context))

HOME = r'''
<section class="heading"><div><div class="eyebrow">CONTENT LIBRARY</div><h1>文案總覽</h1><p>把每一門課的招生內容，整理在同一個地方。</p></div><a class="btn primary" href="{{ url_for('new_course') }}">＋ 新增課程</a></section>
<section class="stats"><div class="stat"><div><div class="statlabel">課程總數 <span>◫</span></div><div class="statval">{{ total }}</div><div class="statnote">已建立的課程專案</div></div></div><div class="stat"><div><div class="statlabel">文案版本 <span>▤</span></div><div class="statval">{{ copies }}</div><div class="statnote">招生、社群與電子郵件</div></div></div><div class="stat"><div><div class="statlabel">內容完整度 <span>◎</span></div><div class="statval">{{ coverage }}<small style="font-size:14px;color:#77817a">%</small></div><div class="statnote"><span class="statdot"></span>平均每門課已備齊的版本</div></div></div></section>
<section id="courses"><div class="toolbar"><form class="search" method="get"><input name="q" value="{{ q }}" placeholder="搜尋課程名稱或類別…"></form><select class="select" onchange="location.href='/?kind='+encodeURIComponent(this.value)+'&q='+encodeURIComponent({{ q|tojson }})"><option value="">所有內容類型</option>{% for k in kinds %}<option value="{{ k }}" {% if kind==k %}selected{% endif %}>{{ k }}</option>{% endfor %}</select></div>
<div class="tablewrap">{% if courses %}<table><thead><tr><th>課程</th><th>類別</th><th>開課日期</th><th>內容版本</th><th style="text-align:right">操作</th></tr></thead><tbody>{% for c in courses %}<tr><td><a class="coursename" href="{{ url_for('course_detail', course_id=c.id) }}">{{ c.name }}</a><div class="subtext">{{ c.audience or '尚未設定目標對象' }}</div></td><td><span class="tag">{{ c.category or '未分類' }}</span></td><td>{{ c.start_date or '—' }}</td><td><div class="chips">{% for k in kinds %}<span class="chip {% if not c[k+'_count'] %}missing{% endif %}">{{ k }} {{ c[k+'_count'] }}</span>{% endfor %}</div></td><td><div class="actions"><a class="iconbtn" title="查看課程" href="{{ url_for('course_detail', course_id=c.id) }}">↗</a><a class="iconbtn" title="編輯課程" href="{{ url_for('edit_course', course_id=c.id) }}">✎</a></div></td></tr>{% endfor %}</tbody></table>{% else %}<div class="empty"><b>還沒有符合條件的課程</b>新增課程，開始整理你的招生內容。<p><a class="btn primary" href="{{ url_for('new_course') }}">＋ 新增課程</a></p></div>{% endif %}</div></section>
'''

COURSE_FORM = r'''
<section class="heading"><div><div class="eyebrow">COURSE PROJECT</div><h1>{{ heading }}</h1><p>建立課程資料，再逐步新增各種招生內容版本。</p></div></section><form method="post" class="formcard"><div class="formgrid"><div class="field full"><label for="name">課程名稱 *</label><input required id="name" name="name" value="{{ course.name if course else '' }}" placeholder="例如：品牌視覺設計實戰班"></div><div class="field"><label for="category">課程類別</label><input id="category" name="category" value="{{ course.category if course else '' }}" placeholder="例如：設計、行銷、程式"></div><div class="field"><label for="start_date">開課日期</label><input id="start_date" name="start_date" type="date" value="{{ course.start_date if course else '' }}"></div><div class="field full"><label for="audience">目標對象</label><input id="audience" name="audience" value="{{ course.audience if course else '' }}" placeholder="例如：想轉職的初階設計師"></div></div><div class="formactions"><a class="btn" href="{{ url_for('index') }}">取消</a><button class="btn primary" type="submit">儲存課程　→</button></div></form>
'''

COPY_FORM = r'''
<section class="heading"><div><div class="eyebrow">CONTENT VERSION · {{ course.name }}</div><h1>{{ heading }}</h1><p>為這門課建立可重複編輯、集中查找的內容版本。</p></div></section><form method="post" class="formcard"><div class="formgrid"><div class="field"><label for="kind">內容類型 *</label><select id="kind" name="kind">{% for k in kinds %}<option value="{{ k }}" {% if copy and copy.kind==k or not copy and kind==k %}selected{% endif %}>{{ k }}</option>{% endfor %}</select></div><div class="field"><label for="title">版本名稱 *</label><input required id="title" name="title" value="{{ copy.title if copy else '' }}" placeholder="例如：早鳥招生主視覺文案"></div><div class="field full"><label for="body">文案內容</label><textarea id="body" name="body" placeholder="在此撰寫或貼上文案…">{{ copy.body if copy else '' }}</textarea></div></div><div class="formactions"><a class="btn" href="{{ url_for('course_detail', course_id=course.id) }}">取消</a><button class="btn primary" type="submit">儲存版本　→</button></div></form>
'''

DETAIL = r'''
<section class="heading"><div><div class="eyebrow">COURSE LIBRARY</div><h1>{{ course.name }}</h1><p>{{ course.category or '未分類' }}{% if course.start_date %}　·　{{ course.start_date }} 開課{% endif %}{% if course.audience %}　·　適合 {{ course.audience }}{% endif %}</p></div><a class="btn primary" href="{{ url_for('new_copy', course_id=course.id) }}">＋ 新增版本</a></section><div class="detailcard"><div class="detailhead"><div><h2>招生內容</h2><p>共 {{ copies|length }} 個版本，最近更新的內容會顯示在前面。</p></div><div class="actions"><a class="btn" href="{{ url_for('edit_course', course_id=course.id) }}">✎ 編輯課程</a><form method="post" action="{{ url_for('delete_course', course_id=course.id) }}" onsubmit="return confirm('將此課程移到垃圾桶嗎？之後可以還原。')"><button class="btn" type="submit">移至垃圾桶</button></form></div></div>{% if copies %}{% for copy in copies %}<article class="copy"><div class="copytop"><div><span class="tag">{{ copy.kind }}</span>　<h3 style="display:inline">{{ copy.title }}</h3></div><div class="actions"><a class="iconbtn" title="編輯版本" href="{{ url_for('edit_copy', copy_id=copy.id) }}">✎</a><form method="post" action="{{ url_for('delete_copy', copy_id=copy.id) }}" onsubmit="return confirm('確定刪除此文案版本？')"><button class="iconbtn" title="刪除版本">×</button></form></div></div><div class="copybody">{{ copy.body or '尚未填寫文案內容。' }}</div><div class="subtext" style="margin-top:8px">更新於 {{ copy.updated_at }}</div></article>{% endfor %}{% else %}<div class="empty"><b>這門課還沒有文案版本</b>新增招生文案、社群貼文或電子郵件版本。</div>{% endif %}</div><p style="margin-top:15px"><a class="muted" href="{{ url_for('index') }}">← 返回文案總覽</a></p>
'''

TRASH = r'''
<section class="heading"><div><div class="eyebrow">RECENTLY DELETED</div><h1>垃圾桶</h1><p>移到垃圾桶的課程可以還原；永久刪除後，課程與所有文案都無法復原。</p></div></section><div class="tablewrap">{% if courses %}<table><thead><tr><th>課程</th><th>類別</th><th>文案版本</th><th>移入時間</th><th style="text-align:right">操作</th></tr></thead><tbody>{% for c in courses %}<tr><td><span class="coursename">{{ c.name }}</span></td><td><span class="tag">{{ c.category or '未分類' }}</span></td><td>{{ c.copy_count }}</td><td>{{ c.deleted_at }}</td><td><div class="actions"><form method="post" action="{{ url_for('restore_course', course_id=c.id) }}"><button class="btn" type="submit">還原</button></form><form method="post" action="{{ url_for('purge_course', course_id=c.id) }}" onsubmit="return confirm('永久刪除這門課及全部文案？此操作無法復原。')"><button class="btn" type="submit" style="color:#a33;border-color:#e8caca">永久刪除</button></form></div></td></tr>{% endfor %}</tbody></table>{% else %}<div class="empty"><b>垃圾桶是空的</b>移到垃圾桶的課程會顯示在這裡。</div>{% endif %}</div><p style="margin-top:15px"><a class="muted" href="{{ url_for('index') }}">← 返回文案總覽</a></p>
'''

@app.get("/")
def index():
    q = request.args.get("q", "").strip()
    kind = request.args.get("kind", "")
    where, params = ["c.deleted_at IS NULL"], []
    if q:
        where.append("(c.name LIKE ? OR c.category LIKE ? OR c.audience LIKE ?)")
        params.extend([f"%{q}%"] * 3)
    if kind in KINDS:
        where.append("EXISTS (SELECT 1 FROM copies f WHERE f.course_id=c.id AND f.kind=?)")
        params.append(kind)
    sql = "SELECT c.*," + ",".join([f"(SELECT COUNT(*) FROM copies x WHERE x.course_id=c.id AND x.kind='{k}') AS '{k}_count'" for k in KINDS]) + " FROM courses c"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY c.id DESC"
    courses = db().execute(sql, params).fetchall()
    total = db().execute("SELECT COUNT(*) FROM courses WHERE deleted_at IS NULL").fetchone()[0]
    copies = db().execute("SELECT COUNT(*) FROM copies x JOIN courses c ON c.id=x.course_id WHERE c.deleted_at IS NULL").fetchone()[0]
    coverage = round(copies / (total * len(KINDS)) * 100) if total else 0
    return page("文案總覽", HOME, courses=courses, total=total, copies=copies, coverage=coverage, q=q, kind=kind, kinds=KINDS)

@app.get("/trash")
def trash():
    courses = db().execute("SELECT c.*, (SELECT COUNT(*) FROM copies x WHERE x.course_id=c.id) AS copy_count FROM courses c WHERE c.deleted_at IS NOT NULL ORDER BY c.deleted_at DESC, c.id DESC").fetchall()
    return page("垃圾桶", TRASH, courses=courses)

@app.route("/courses/new", methods=["GET", "POST"])
def new_course():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("請填寫課程名稱。")
        else:
            cur = db().execute("INSERT INTO courses(name,category,audience,start_date,created_at) VALUES(?,?,?,?,?)", (name, request.form.get("category", "").strip(), request.form.get("audience", "").strip(), request.form.get("start_date", ""), datetime.now().strftime("%Y-%m-%d %H:%M")))
            db().commit()
            flash("課程已建立，可以開始新增文案版本。")
            return redirect(url_for("course_detail", course_id=cur.lastrowid))
    return page("新增課程", COURSE_FORM, heading="新增課程", course=None)

@app.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
def edit_course(course_id):
    course = db().execute("SELECT * FROM courses WHERE id=? AND deleted_at IS NULL", (course_id,)).fetchone()
    if not course: abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            db().execute("UPDATE courses SET name=?,category=?,audience=?,start_date=? WHERE id=?", (name, request.form.get("category", "").strip(), request.form.get("audience", "").strip(), request.form.get("start_date", ""), course_id))
            db().commit(); flash("課程資料已更新。")
            return redirect(url_for("course_detail", course_id=course_id))
        flash("請填寫課程名稱。")
    return page("編輯課程", COURSE_FORM, heading="編輯課程", course=course)

@app.get("/courses/<int:course_id>")
def course_detail(course_id):
    course = db().execute("SELECT * FROM courses WHERE id=? AND deleted_at IS NULL", (course_id,)).fetchone()
    if not course: abort(404)
    copies = db().execute("SELECT * FROM copies WHERE course_id=? ORDER BY updated_at DESC,id DESC", (course_id,)).fetchall()
    return page("課程內容", DETAIL, course=course, copies=copies)

@app.post("/courses/<int:course_id>/delete")
def delete_course(course_id):
    course = db().execute("SELECT name FROM courses WHERE id=? AND deleted_at IS NULL", (course_id,)).fetchone()
    if not course:
        abort(404)
    db().execute("UPDATE courses SET deleted_at=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M"), course_id))
    db().commit()
    flash(f"課程「{course['name']}」已移至垃圾桶，可以還原。")
    return redirect(url_for("index"))

@app.post("/courses/<int:course_id>/restore")
def restore_course(course_id):
    course = db().execute("SELECT name FROM courses WHERE id=? AND deleted_at IS NOT NULL", (course_id,)).fetchone()
    if not course:
        abort(404)
    db().execute("UPDATE courses SET deleted_at=NULL WHERE id=?", (course_id,))
    db().commit()
    flash(f"課程「{course['name']}」已還原。")
    return redirect(url_for("trash"))

@app.post("/courses/<int:course_id>/purge")
def purge_course(course_id):
    course = db().execute("SELECT name FROM courses WHERE id=? AND deleted_at IS NOT NULL", (course_id,)).fetchone()
    if not course:
        abort(404)
    db().execute("DELETE FROM courses WHERE id=?", (course_id,))
    db().commit()
    flash(f"課程「{course['name']}」及其文案已永久刪除。")
    return redirect(url_for("trash"))

@app.route("/courses/<int:course_id>/copies/new", methods=["GET", "POST"])
def new_copy(course_id):
    course = db().execute("SELECT * FROM courses WHERE id=? AND deleted_at IS NULL", (course_id,)).fetchone()
    if not course: abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        kind = request.form.get("kind", "")
        if not title or kind not in KINDS:
            flash("請填寫版本名稱並選擇內容類型。")
        else:
            db().execute("INSERT INTO copies(course_id,kind,title,body,updated_at) VALUES(?,?,?,?,?)", (course_id,kind,title,request.form.get("body", "").strip(),datetime.now().strftime("%Y-%m-%d %H:%M")))
            db().commit(); flash("文案版本已儲存。")
            return redirect(url_for("course_detail", course_id=course_id))
    return page("新增文案", COPY_FORM, heading="新增文案版本", course=course, copy=None, kinds=KINDS, kind=request.args.get("kind", ""))

@app.route("/copies/<int:copy_id>/edit", methods=["GET", "POST"])
def edit_copy(copy_id):
    copy = db().execute("SELECT * FROM copies WHERE id=?", (copy_id,)).fetchone()
    if not copy: abort(404)
    course = db().execute("SELECT * FROM courses WHERE id=? AND deleted_at IS NULL", (copy["course_id"],)).fetchone()
    if not course:
        abort(404)
    if request.method == "POST":
        title, kind = request.form.get("title", "").strip(), request.form.get("kind", "")
        if not title or kind not in KINDS:
            flash("請填寫版本名稱並選擇內容類型。")
        else:
            db().execute("UPDATE copies SET title=?,kind=?,body=?,updated_at=? WHERE id=?", (title,kind,request.form.get("body", "").strip(),datetime.now().strftime("%Y-%m-%d %H:%M"),copy_id))
            db().commit(); flash("文案版本已更新。")
            return redirect(url_for("course_detail", course_id=course["id"]))
    return page("編輯文案", COPY_FORM, heading="編輯文案版本", course=course, copy=copy, kinds=KINDS, kind=copy["kind"])

@app.post("/copies/<int:copy_id>/delete")
def delete_copy(copy_id):
    copy = db().execute("SELECT course_id FROM copies WHERE id=?", (copy_id,)).fetchone()
    if copy:
        course_id = copy["course_id"]
        db().execute("DELETE FROM copies WHERE id=?", (copy_id,)); db().commit(); flash("文案版本已刪除。")
        return redirect(url_for("course_detail", course_id=course_id))
    abort(404)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
