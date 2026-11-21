import hmac, os, re, secrets, subprocess, threading, time, shutil, json, hashlib
from pathlib import Path
from urllib.parse import quote
from flask import Flask, abort, flash, redirect, render_template_string, request, send_file, session, url_for
from werkzeug.utils import secure_filename

ROOT = Path(os.environ.get("VAULT_ROOT", "/vault")).resolve()
SOURCE = Path(os.environ.get("SOURCE_ROOT", "/source")).resolve()
APP_DATA_ROOT = Path(os.environ.get("APP_DATA_ROOT", "/app-data")).resolve()
UNLOCKED = ROOT / "Unlocked"
DATA = Path(os.environ.get("APP_DATA_DIR", "/data"))
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
PORT = int(os.environ.get("PORT", "8088"))
DATA.mkdir(parents=True, exist_ok=True)
mount_config_dir = DATA / "mount-locations"
mount_config_dir.mkdir(parents=True, exist_ok=True)
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
</div>
{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}</main></body></html>
"""
HOME = r"""
<section class="card"><h2>Create encrypted vault</h2><form method="post" action="/create">
<input type="hidden" name="csrf" value="{{csrf}}"><label>Vault name</label>
<input name="name" pattern="[A-Za-z0-9_-]{1,48}" placeholder="Personal" required>
<label>Encrypted vault storage folder</label>
<input name="location" value="{{location}}" readonly required>
<a href="/pick?kind=storage&path={{location|urlencode}}">Choose directory…</a>
<label>Where should the unlocked folder appear?</label>
<input name="unlock_location" value="{{unlock_location}}" readonly required>
<a href="/pick?kind=unlocked&path={{unlock_location|urlencode}}">Choose unlocked folder location…</a>
<small>The picker starts in the same directory as the encrypted vault location. The decrypted mount will appear in an Unlocked subfolder beneath your selection.</small>
<label>Vault password</label><input type="password" name="password" minlength="8" required>
<button>Create vault</button></form><small>Choose a folder on the Toshiba drive. Save the recovery key separately.</small></section>
<section class="card"><h2>Your vaults</h2>{% if vaults %}<div class="grid">{% for v in vaults %}
<div class="vault"><div class="row"><b>📁 {{v.name}}</b><span class="pill {{'open' if v.open else ''}}">{{'UNLOCKED' if v.open else 'LOCKED'}}</span></div>
<small>Location: {{v.location}}</small>
{% if v.open %}<p><a href="/browse/{{v.key|urlencode}}">Browse files →</a></p>
<form method="post" action="/lock/{{v.key}}"><input type="hidden" name="csrf" value="{{csrf}}"><button class="danger">Lock vault</button></form>
{% else %}<form method="post" action="/unlock/{{v.key}}"><input type="hidden" name="csrf" value="{{csrf}}">
<label>Vault password</label><input type="password" name="password" required><button>Unlock</button></form>{% endif %}
{% if not v.open %}<form method="post" action="/delete/{{v.key}}" onsubmit="return confirm('Permanently delete this encrypted vault and ALL its contents? This cannot be undone.');"><input type="hidden" name="csrf" value="{{csrf}}"><label>Type DELETE to confirm</label><input name="confirm" required pattern="DELETE"><button class="danger">Delete vault permanently</button></form>{% endif %}
</div>{% endfor %}</div>{% else %}<p class="muted">No vaults yet.</p>{% endif %}</section>
<section class="card"><h2>File browser</h2><p><a href="/source">Browse files on your Toshiba drive and copy them into an unlocked vault →</a></p></section>
<section class="card"><h2>Storage</h2><small>Encrypted vaults</small><div class="path">{{root}}</div><small>Unlocked mounts</small><div class="path">{{unlocked}}</div></section>
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
SOURCE_BROWSER = r"""
<section class="card"><p><a href="/">← Vault Manager</a></p><h2>Browse Toshiba drive</h2>
<p class="muted">Select files or folders, choose an unlocked vault, and copy them into it. The source drive is read-only to this app.</p>
{% if parent is not none %}<p><a href="/source?path={{parent|urlencode}}">← Parent folder</a></p>{% endif %}
<form method="post" action="/source-copy"><input type="hidden" name="csrf" value="{{csrf}}"><input type="hidden" name="path" value="{{relative}}">
<label>Copy selected items into</label><select name="vault" required>{% for v in open_vaults %}<option value="{{v}}">{{v}}</option>{% endfor %}</select>
<div style="margin:12px 0"><button type="button" class="secondary" onclick="document.querySelectorAll('input[name=items]').forEach(x=>x.checked=true)">Select all</button> <button type="submit">Copy selected into vault</button></div>
{% for x in items %}<div class="file"><label style="display:flex;align-items:center;gap:10px"><input style="width:auto;margin:0" type="checkbox" name="items" value="{{x.rel}}"><span>{% if x.dir %}📁 <a href="/source?path={{x.rel|urlencode}}">{{x.name}}/</a>{% else %}📄 {{x.name}}{% endif %}</span></label></div>{% else %}<p class="muted">No files in this folder.</p>{% endfor %}</form></section>
"""

PICKER = r"""
<section class="card"><p><a href="/">← Cancel and return</a></p><h2>{{title}}</h2>
<p class="muted">{{help_text}}</p>
<div class="path">{{root if not current else root ~ "/" ~ current}}</div>
<form method="post" action="/select-location"><input type="hidden" name="csrf" value="{{csrf}}">
<input type="hidden" name="kind" value="{{kind}}">
<input type="hidden" name="location" value="{{current}}">
<button>Select this folder</button></form>
{% if parent is not none %}<p><a href="/pick?path={{parent|urlencode}}">← Parent folder</a></p>{% endif %}
{% for x in items %}<div class="file"><span>📁 <a href="/pick?path={{x.rel|urlencode}}">{{x.name}}/</a></span></div>{% else %}<p class="muted">No subfolders here.</p>{% endfor %}
</section>
"""
def token():
    if "csrf" not in session: session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]
@app.before_request
def request_guards():
    if request.method == "POST":
        if not session.get("csrf") or not hmac.compare_digest(session["csrf"], request.form.get("csrf", "")):
            abort(400)
def page(body, **kw):
    return render_template_string(SHELL, body=body, logged=session.get("logged",False), csrf=token(), **kw)
def valid(n): return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,48}", n or ""))
def valid_key(k):
    if not k or "\\\\" in k:
        return False
    parts = Path(k).parts
    if len(parts) < 2 or parts[0] not in ("appdata", "vault"):
        return False
    return all(part not in ("", ".", "..", "Unlocked") and valid(part) for part in parts[1:])

def enc_path(k):
    if not valid_key(k): abort(404)
    parts = Path(k).parts
    base = APP_DATA_ROOT if parts[0] == "appdata" else ROOT
    return safe(base, Path(*parts[1:]))

def mount_config_file(k):
    digest = hashlib.sha256(k.encode("utf-8")).hexdigest()
    return mount_config_dir / (digest + ".json")

def unlocked_parent_rel(k):
    cfg = mount_config_file(k)
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            if data.get("vault_key") == k:
                rel = data.get("unlocked_parent", "")
                return safe(APP_DATA_ROOT, rel)
        except (OSError, ValueError, TypeError):
            pass
    # Existing vaults retain their previous default mount location.
    return enc_path(k).parent

def mount_path(k):
    if not valid_key(k): abort(404)
    parent = unlocked_parent_rel(k)
    return safe(parent / "Unlocked", enc_path(k).name)

def save_unlocked_location(k, rel):
    parent = safe(APP_DATA_ROOT, rel)
    if not parent.is_dir():
        raise ValueError("The selected unlocked-folder location does not exist.")
    cfg = mount_config_file(k)
    tmp = cfg.with_suffix(".tmp")
    tmp.write_text(json.dumps({"vault_key": k, "unlocked_parent": rel}), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(cfg)

def vault_records():
    records=[]
    # New vaults are stored beneath APP_DATA_ROOT; legacy vaults remain discoverable in ROOT.
    for base, prefix in ((APP_DATA_ROOT, "appdata"), (ROOT, "vault")):
        try:
            for conf in base.rglob("gocryptfs.conf"):
                rel=conf.parent.relative_to(base)
                if not rel.parts or rel.parts[0] == "Unlocked": continue
                key=(Path(prefix)/rel).as_posix()
                if valid_key(key):
                    records.append({"key":key,"name":conf.parent.name,
                        "location":str(rel.parent) if str(rel.parent)!="." else "Root",
                        "open":mounted(mount_path(key))})
        except OSError:
            continue
    return sorted(records,key=lambda x:x["key"].lower())

def location_options(rel=""):
    # Directory picker is confined to APP_DATA_ROOT.
    cur=safe(APP_DATA_ROOT, rel)
    if not cur.is_dir(): abort(404)
    options=[]
    try:
        for p in sorted(cur.iterdir(), key=lambda x:x.name.lower()):
            try:
                if p.is_symlink() or not p.is_dir(): continue
                child_rel=p.relative_to(APP_DATA_ROOT).as_posix()
                options.append({"name":p.name,"rel":child_rel})
            except OSError:
                continue
    except OSError:
        pass
    parent=str(Path(rel).parent) if rel and str(Path(rel).parent)!="." else None
    return options, parent, rel

def mounted(p): return os.path.ismount(p)
@app.get("/")
def home():
    vaults=vault_records()
    location=session.get("new_vault_location","")
    unlock_location=session.get("new_unlocked_location",location)
    return page(render_template_string(HOME,logged=True,csrf=token(),
        vaults=vaults,location=location,unlock_location=unlock_location,
        root=str(APP_DATA_ROOT),unlocked=str(UNLOCKED)))

@app.get("/pick")
def pick_location():
    kind=request.args.get("kind","storage")
    if kind not in ("storage","unlocked"): abort(400)
    if kind == "unlocked":
        start=session.get("new_vault_location","")
        rel=request.args.get("path",start)
        title="Choose unlocked folder location"
        help_text="Choose the parent directory for the Unlocked/<vault-name> mount."
    else:
        rel=request.args.get("path","")
        title="Choose encrypted vault storage folder"
        help_text="Choose where the encrypted vault directory will be created."
    items,parent,current=location_options(rel)
    return page(render_template_string(PICKER,items=items,parent=parent,current=current,
        root=str(APP_DATA_ROOT),title=title,help_text=help_text,kind=kind,csrf=token()))

@app.post("/select-location")
def select_location():
    rel=request.form.get("location","")
    kind=request.form.get("kind","storage")
    if kind not in ("storage","unlocked"): abort(400)
    safe(APP_DATA_ROOT, rel)
    if rel and not safe(APP_DATA_ROOT, rel).is_dir(): abort(400)
    if kind == "storage":
        session["new_vault_location"]=rel
        session["new_unlocked_location"]=rel
        flash("Encrypted vault storage folder selected.")
    else:
        session["new_unlocked_location"]=rel
        flash("Unlocked folder location selected.")
    return redirect("/")
@app.post("/create")
def create():
    n,pw=request.form.get("name",""),request.form.get("password","")
    location=request.form.get("location","")
    unlock_location=request.form.get("unlock_location","")
    if not valid(n) or len(pw)<8:
        flash("Invalid name or password (minimum 8 characters)."); return redirect("/")
    try:
        parent=safe(APP_DATA_ROOT,location)
    except Exception:
        flash("Invalid storage folder."); return redirect("/")
    if not parent.is_dir():
        flash("Invalid storage folder."); return redirect("/")
    key=(Path("appdata")/location/n).as_posix() if location else (Path("appdata")/n).as_posix()
    enc=enc_path(key)
    if enc.exists(): flash("A vault with that name already exists at this location."); return redirect("/")
    try:
        selected_unlock_parent=safe(APP_DATA_ROOT,unlock_location)
        if not selected_unlock_parent.is_dir(): raise ValueError("Invalid unlocked-folder location.")
    except Exception:
        flash("Invalid unlocked-folder location."); return redirect("/")
    enc.mkdir(mode=0o700)
    save_unlocked_location(key, unlock_location)
    mnt=mount_path(key)
    mnt.mkdir(parents=True,exist_ok=True,mode=0o700)
    try:
        r=subprocess.run(["gocryptfs","-init","-passfile","/dev/stdin",str(enc)],
            input=(pw+"\n").encode(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        output=r.stdout.decode(errors="replace")
        if r.returncode: flash("Creation failed: "+output[-700:]); return redirect("/")
        session.pop("new_vault_location", None)
        session.pop("new_unlocked_location", None)
        return page(render_template_string("""<section class="card"><h2>Vault created: {{n}}</h2>
<p><b>Save this recovery key now.</b> Store it separately from the Toshiba drive.</p><pre>{{output}}</pre><a href="/">Return to Vault Manager</a></section>""",n=n,output=output))
    except Exception as e: flash("Creation failed: "+str(e)); return redirect("/")
@app.post("/unlock/<path:n>")
def unlock(n):
    if not valid_key(n): abort(404)
    enc,mnt=enc_path(n),mount_path(n)
    if not (enc/"gocryptfs.conf").is_file(): abort(404)
    mnt.mkdir(parents=True,exist_ok=True)
    if mounted(mnt): flash("Already unlocked."); return redirect("/")
    if any(mnt.iterdir()): flash("Unlocked mount folder must be empty."); return redirect("/")
    proc=subprocess.Popen(["gocryptfs","-fg","-allow_other","-passfile","/dev/stdin",str(enc),str(mnt)],
        stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    proc.stdin.write((request.form.get("password","")+"\n").encode()); proc.stdin.close()
    with children_lock: children[n]=proc
    for _ in range(50):
        if mounted(mnt): flash("Vault unlocked."); return redirect("/")
        if proc.poll() is not None:
            err=proc.stderr.read().decode(errors="replace")[-800:]; flash("Unlock failed: "+err); return redirect("/")
        time.sleep(.2)
    flash("Mount did not start. Check FUSE and mount propagation."); return redirect("/")
@app.post("/lock/<path:n>")
def lock(n):
    if not valid_key(n): abort(404)
    mnt=mount_path(n)
    if not mounted(mnt): flash("Already locked."); return redirect("/")
    r=subprocess.run(["fusermount3","-u",str(mnt)],capture_output=True,text=True)
    if r.returncode: flash("Lock failed: "+r.stderr[-500:])
    else:
        with children_lock: children.pop(n,None)
        flash("Vault locked.")
    return redirect("/")
@app.post("/delete/<path:n>")
def delete_vault(n):
    if not valid_key(n): abort(404)
    enc=enc_path(n); mnt=mount_path(n)
    if not (enc/"gocryptfs.conf").is_file(): abort(404)
    if mounted(mnt):
        flash("Lock this vault before deleting it."); return redirect("/")
    if request.form.get("confirm") != "DELETE":
        flash("Deletion not confirmed."); return redirect("/")
    try:
        shutil.rmtree(enc)
        # Remove the empty mount directory only; never remove the Unlocked root.
        if mnt.exists() and not any(mnt.iterdir()): mnt.rmdir()
        with children_lock: children.pop(n,None)
        flash("Vault permanently deleted.")
    except Exception as e:
        flash("Delete failed: "+str(e))
    return redirect("/")

def safe(root,rel):
    p=(root/rel).resolve()
    if p!=root and root not in p.parents: abort(403)
    return p
@app.get("/browse/<path:n>")
def browse(n):
    if not valid_key(n): abort(404)
    root=mount_path(n).resolve()
    if not mounted(root): abort(404)
    rel=request.args.get("path",""); cur=safe(root,rel)
    if not cur.is_dir(): abort(404)
    items=[]
    for p in sorted(cur.iterdir(),key=lambda x:(not x.is_dir(),x.name.lower())):
        if p.is_symlink(): continue
        items.append({"name":p.name,"dir":p.is_dir(),"rel":str(p.relative_to(root))})
    parent=str(Path(rel).parent) if rel and str(Path(rel).parent)!="." else None
    return page(render_template_string(BROWSE,name=n,items=items,relative=rel,parent=parent,csrf=token()))
@app.post("/upload/<path:n>")
def upload(n):
    if not valid_key(n): abort(404)
    root=mount_path(n).resolve()
    if not mounted(root): abort(404)
    rel=request.args.get("path",""); dest=safe(root,rel)
    if not dest.is_dir(): abort(404)
    count=0
    for f in request.files.getlist("files"):
        name=secure_filename(f.filename or "")
        if name and not (dest/name).exists(): f.save(dest/name); count+=1
    flash(f"Uploaded {count} file(s)."); return redirect(url_for("browse",n=n,path=rel))
@app.get("/download/<path:n>/<path:rel>")
def download(n,rel):
    if not valid_key(n): abort(404)
    root=mount_path(n).resolve()
    if not mounted(root): abort(404)
    p=safe(root,rel)
    if not p.is_file() or p.is_symlink(): abort(404)
    return send_file(p,as_attachment=True)
@app.get("/source")
def source_browser():
    rel=request.args.get("path","")
    if rel and Path(rel).parts and Path(rel).parts[0] == "Vault": abort(404)
    cur=safe(SOURCE,rel)
    if not cur.is_dir(): abort(404)
    items=[]
    for p in sorted(cur.iterdir(),key=lambda x:(not x.is_dir(),x.name.lower())):
        # Never expose the encrypted vault container or its mount tree through the source picker.
        if not rel and p.name == "Vault": continue
        if p.is_symlink(): continue
        items.append({"name":p.name,"dir":p.is_dir(),"rel":str(p.relative_to(SOURCE))})
    parent=str(Path(rel).parent) if rel and str(Path(rel).parent)!="." else None
    open_vaults=[v["key"] for v in vault_records() if v["open"]]
    return page(render_template_string(SOURCE_BROWSER,items=items,relative=rel,parent=parent,csrf=token(),open_vaults=open_vaults))

@app.post("/source-copy")
def source_copy():
    rel=request.form.get("path","")
    if rel and Path(rel).parts and Path(rel).parts[0] == "Vault": abort(404)
    vault=request.form.get("vault","")
    if not valid_key(vault): abort(400)
    srcroot=mount_path(vault).resolve()
    if not mounted(srcroot): abort(400)
    current=safe(SOURCE,rel)
    if not current.is_dir(): abort(400)
    selected=request.form.getlist("items")
    if not selected: flash("Select at least one file or folder."); return redirect(url_for("source_browser",path=rel))
    copied=0; skipped=0
    for item in selected:
        source=safe(SOURCE,item)
        if source==SOURCE or not source.exists() or source.is_symlink(): skipped+=1; continue
        # Each selected entry must be directly inside the folder currently being browsed.
        if source.parent != current: skipped+=1; continue
        dest=srcroot/source.name
        if dest.exists(): skipped+=1; continue
        try:
            if source.is_dir():
                shutil.copytree(source,dest,symlinks=True)
            elif source.is_file(): shutil.copy2(source,dest)
            else: skipped+=1; continue
            copied+=1
        except Exception:
            skipped+=1
    flash(f"Copied {copied} item(s) into {vault}; skipped {skipped}.")
    return redirect(url_for("browse",n=vault))

if __name__=="__main__": app.run(host="0.0.0.0",port=PORT,threaded=True)
