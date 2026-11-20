import hmac, os, re, secrets, subprocess, threading, time
from pathlib import Path
from urllib.parse import quote
from flask import Flask, abort, flash, redirect, render_template_string, request, send_file, session, url_for
from werkzeug.utils import secure_filename

ROOT = Path(os.environ.get("VAULT_ROOT", "/vault")).resolve()
UNLOCKED = ROOT / "Unlocked"
DATA = Path(os.environ.get("APP_DATA_DIR", "/data"))
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
PORT = int(os.environ.get("PORT", "8088"))
if not APP_PASSWORD:
    raise RuntimeError("APP_PASSWORD is required.")
DATA.mkdir(parents=True, exist_ok=True)
secret_file = DATA / "session-secret"
if not secret_file.exists():
    secret_file.write_text(secrets.token_urlsafe(48))
    secret_file.chmod(0o600)
app = Flask(__name__)
app.secret_key = secret_file.read_text().strip()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                  MAX_CONTENT_LENGTH=512 * 1024 * 1024)
ROOT.mkdir(parents=True, exist_ok=True)
UNLOCKED.mkdir(parents=True, exist_ok=True)
children, children_lock = {}, threading.Lock()

SHELL = r"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vault Manager</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101720;color:#eaf0f8;font:15px system-ui}
main{max-width:960px;margin:34px auto;padding:0 18px}.head{display:flex;justify-content:space-between;align-items:center;gap:12px}
h1{font-size:25px;margin:0}h2{font-size:18px;margin:0 0 14px}.muted,small{color:#9aaabd}
.card,.vault{background:#192533;border:1px solid #304257;border-radius:13px;padding:18px;margin:16px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.vault{margin:0;background:#111d2a}.row{display:flex;justify-content:space-between;align-items:center;gap:10px}
input,button{font:inherit;border-radius:9px;padding:10px 12px;border:1px solid #40536b}
input{width:100%;background:#0c1520;color:#fff;margin:5px 0 12px}button{background:#d9e8fb;color:#102034;font-weight:700;cursor:pointer}
button.secondary{background:#293a4e;color:#edf3fb}button.danger{background:#702d38;color:white}
label{display:block;color:#bfccdc;font-size:13px}.pill{font-size:11px;border-radius:20px;padding:4px 8px;background:#2b3b4f}
.pill.open{background:#164c39;color:#aaf0ce}.flash{padding:10px 13px;background:#263a50;border-radius:9px;margin:12px 0}
a{color:#a9ceff;text-decoration:none}a:hover{text-decoration:underline}.path{overflow-wrap:anywhere;background:#0b141e;padding:9px;border-radius:8px}
.file{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #304257;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b141e;padding:14px;border-radius:9px}
</style></head><body><main><div class="head"><div><h1>🔐 Vault Manager</h1><small>Encrypted storage on your Toshiba drive</small></div>
{% if logged %}<form method="post" action="/logout"><input type="hidden" name="csrf" value="{{csrf}}"><button class="secondary">Log out</button></form>{% endif %}</div>
{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}</main></body></html>
"""
HOME = r"""
{% if not logged %}<section class="card"><h2>Sign in</h2><form method="post" action="/login">
<input type="hidden" name="csrf" value="{{csrf}}"><label>Umbrel app password</label>
<input type="password" name="password" required autofocus><button>Sign in</button></form></section>
{% else %}
<section class="card"><h2>Create encrypted vault</h2><form method="post" action="/create">
<input type="hidden" name="csrf" value="{{csrf}}"><label>Vault name</label>
<input name="name" pattern="[A-Za-z0-9_-]{1,48}" placeholder="Personal" required>
<label>Vault password</label><input type="password" name="password" minlength="8" required>
<button>Create vault</button></form><small>Save the recovery key displayed after creation somewhere safe and separate from this drive.</small></section>
<section class="card"><h2>Your vaults</h2>{% if vaults %}<div class="grid">{% for v in vaults %}
<div class="vault"><div class="row"><b>📁 {{v.name}}</b><span class="pill {{'open' if v.open else ''}}">{{'UNLOCKED' if v.open else 'LOCKED'}}</span></div>
{% if v.open %}<p><a href="/browse/{{v.name}}">Browse files →</a></p>
<form method="post" action="/lock/{{v.name}}"><input type="hidden" name="csrf" value="{{csrf}}"><button class="danger">Lock vault</button></form>
{% else %}<form method="post" action="/unlock/{{v.name}}"><input type="hidden" name="csrf" value="{{csrf}}">
<label>Vault password</label><input type="password" name="password" required><button>Unlock</button></form>{% endif %}
</div>{% endfor %}</div>{% else %}<p class="muted">No vaults yet.</p>{% endif %}</section>
<section class="card"><h2>Storage</h2><small>Encrypted vaults</small><div class="path">{{root}}</div>
<small>Unlocked mounts</small><div class="path">{{unlocked}}</div></section>{% endif %}
"""
BROWSE = r"""
<section class="card"><p><a href="/">← All vaults</a></p><div class="row"><h2>📂 {{name}}</h2>
<form method="post" action="/lock/{{name}}"><input type="hidden" name="csrf" value="{{csrf}}"><button class="danger">Lock vault</button></form></div>
<small>/{{relative}}</small>{% if parent is not none %}<p><a href="/browse/{{name}}?path={{parent|urlencode}}">← Parent folder</a></p>{% endif %}
<form method="post" enctype="multipart/form-data" action="/upload/{{name}}?path={{relative|urlencode}}">
<input type="hidden" name="csrf" value="{{csrf}}"><label>Upload files</label><input type="file" name="files" multiple required><button>Upload</button></form>
{% for x in items %}<div class="file"><span>{% if x.dir %}📁 <a href="/browse/{{name}}?path={{x.rel|urlencode}}">{{x.name}}/</a>{% else %}📄 {{x.name}}{% endif %}</span>
{% if not x.dir %}<a href="/download/{{name}}/{{x.rel}}">Download</a>{% endif %}</div>{% else %}<p class="muted">Folder is empty.</p>{% endfor %}</section>
"""
def token():
    if "csrf" not in session: session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]
@app.before_request
def request_guards():
    # Require dashboard authentication for every endpoint except the login page
    # and root (which intentionally renders the sign-in form).
    if request.endpoint not in ("home", "login", "static") and not session.get("logged"):
        return redirect(url_for("home"))
    if request.method == "POST":
        if not session.get("csrf") or not hmac.compare_digest(session["csrf"], request.form.get("csrf", "")):
            abort(400)
def page(body, **kw):
    return render_template_string(SHELL, body=body, logged=session.get("logged",False), csrf=token(), **kw)
def valid(n): return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,48}", n or ""))
def mounted(p): return os.path.ismount(p)
@app.get("/")
def home():
    vaults=[]
    if session.get("logged"):
        for p in sorted(ROOT.iterdir()):
            if p.is_dir() and p.name!="Unlocked" and (p/"gocryptfs.conf").is_file():
                vaults.append({"name":p.name,"open":mounted(UNLOCKED/p.name)})
    return page(render_template_string(HOME,logged=session.get("logged",False),csrf=token(),
        vaults=vaults,root=str(ROOT),unlocked=str(UNLOCKED)))
@app.post("/login")
def login():
    if hmac.compare_digest(request.form.get("password",""),APP_PASSWORD):
        session.clear(); session["logged"]=True; session["csrf"]=secrets.token_urlsafe(24)
    else: flash("Incorrect app password.")
    return redirect("/")
@app.post("/logout")
def logout(): session.clear(); return redirect("/")
@app.post("/create")
def create():
    n,pw=request.form.get("name",""),request.form.get("password","")
    if not valid(n) or len(pw)<8: flash("Invalid name or password (minimum 8 characters)."); return redirect("/")
    enc,mnt=ROOT/n,UNLOCKED/n
    if enc.exists(): flash("That vault name already exists."); return redirect("/")
    enc.mkdir(mode=0o700); mnt.mkdir(parents=True,exist_ok=True,mode=0o700)
    try:
        r=subprocess.run(["gocryptfs","-init","-passfile","/dev/stdin",str(enc)],
            input=(pw+"\n").encode(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        output=r.stdout.decode(errors="replace")
        if r.returncode: flash("Creation failed: "+output[-700:]); return redirect("/")
        return page(render_template_string("""<section class="card"><h2>Vault created: {{n}}</h2>
<p><b>Save this recovery key now.</b> Store it separately from the Toshiba drive.</p><pre>{{output}}</pre><a href="/">Return to Vault Manager</a></section>""",n=n,output=output))
    except Exception as e: flash("Creation failed: "+str(e)); return redirect("/")
@app.post("/unlock/<n>")
def unlock(n):
    if not valid(n): abort(404)
    enc,mnt=ROOT/n,UNLOCKED/n
    if not (enc/"gocryptfs.conf").is_file(): abort(404)
    mnt.mkdir(parents=True,exist_ok=True)
    if mounted(mnt): flash("Already unlocked."); return redirect("/")
    if any(mnt.iterdir()): flash("Unlocked mount folder must be empty."); return redirect("/")
    proc=subprocess.Popen(["gocryptfs","-fg","-allow_other","-o","uid=1000,gid=1000","-passfile","/dev/stdin",str(enc),str(mnt)],
        stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    proc.stdin.write((request.form.get("password","")+"\n").encode()); proc.stdin.close()
    with children_lock: children[n]=proc
    for _ in range(50):
        if mounted(mnt): flash("Vault unlocked."); return redirect("/")
        if proc.poll() is not None:
            err=proc.stderr.read().decode(errors="replace")[-800:]; flash("Unlock failed: "+err); return redirect("/")
        time.sleep(.2)
    flash("Mount did not start. Check FUSE and mount propagation."); return redirect("/")
@app.post("/lock/<n>")
def lock(n):
    if not valid(n): abort(404)
    mnt=UNLOCKED/n
    if not mounted(mnt): flash("Already locked."); return redirect("/")
    r=subprocess.run(["fusermount3","-u",str(mnt)],capture_output=True,text=True)
    if r.returncode: flash("Lock failed: "+r.stderr[-500:])
    else:
        with children_lock: children.pop(n,None)
        flash("Vault locked.")
    return redirect("/")
def safe(root,rel):
    p=(root/rel).resolve()
    if p!=root and root not in p.parents: abort(403)
    return p
@app.get("/browse/<n>")
def browse(n):
    if not valid(n): abort(404)
    root=(UNLOCKED/n).resolve()
    if not mounted(root): abort(404)
    rel=request.args.get("path",""); cur=safe(root,rel)
    if not cur.is_dir(): abort(404)
    items=[]
    for p in sorted(cur.iterdir(),key=lambda x:(not x.is_dir(),x.name.lower())):
        if p.is_symlink(): continue
        items.append({"name":p.name,"dir":p.is_dir(),"rel":str(p.relative_to(root))})
    parent=str(Path(rel).parent) if rel and str(Path(rel).parent)!="." else None
    return page(render_template_string(BROWSE,name=n,items=items,relative=rel,parent=parent,csrf=token()))
@app.post("/upload/<n>")
def upload(n):
    if not valid(n): abort(404)
    root=(UNLOCKED/n).resolve()
    if not mounted(root): abort(404)
    rel=request.args.get("path",""); dest=safe(root,rel)
    if not dest.is_dir(): abort(404)
    count=0
    for f in request.files.getlist("files"):
        name=secure_filename(f.filename or "")
        if name and not (dest/name).exists(): f.save(dest/name); count+=1
    flash(f"Uploaded {count} file(s)."); return redirect(url_for("browse",n=n,path=rel))
@app.get("/download/<n>/<path:rel>")
def download(n,rel):
    if not valid(n): abort(404)
    root=(UNLOCKED/n).resolve()
    if not mounted(root): abort(404)
    p=safe(root,rel)
    if not p.is_file() or p.is_symlink(): abort(404)
    return send_file(p,as_attachment=True)
if __name__=="__main__": app.run(host="0.0.0.0",port=PORT,threaded=True)
