import os, sqlite3, secrets
from functools import wraps
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
DB = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "sekolah.db"))

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, display_name TEXT NOT NULL, student_id INTEGER, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, nis TEXT, name TEXT NOT NULL, class_name TEXT, gender TEXT);
        CREATE TABLE IF NOT EXISTS teachers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, subject TEXT, email TEXT);
        CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, attendance_date TEXT NOT NULL, status TEXT NOT NULL, notes TEXT, FOREIGN KEY(student_id) REFERENCES students(id));
        CREATE TABLE IF NOT EXISTS schedules(id INTEGER PRIMARY KEY, class_name TEXT NOT NULL, day_name TEXT NOT NULL, start_time TEXT, subject TEXT NOT NULL, teacher TEXT);
        CREATE TABLE IF NOT EXISTS grades(id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, subject TEXT NOT NULL, assessment TEXT, score REAL, FOREIGN KEY(student_id) REFERENCES students(id));
        CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY, title TEXT NOT NULL, subject TEXT, class_name TEXT, description TEXT, material_url TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS ppdb(id INTEGER PRIMARY KEY, student_name TEXT NOT NULL, parent_name TEXT, phone TEXT, previous_school TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)
        if not c.execute("SELECT 1 FROM announcements LIMIT 1").fetchone():
            c.execute("INSERT INTO announcements(title,content) VALUES(?,?)",("Selamat Datang","Website resmi SMAN 7 Toraja Utara."))
        if not c.execute("SELECT 1 FROM teachers LIMIT 1").fetchone():
            c.execute("INSERT INTO teachers(name,subject) VALUES(?,?)",("Ulfa Ramadhani, S.Pd.","Informatika"))
        if not c.execute("SELECT 1 FROM materials LIMIT 1").fetchone():
            c.execute("INSERT INTO materials(title,subject,class_name,description) VALUES(?,?,?,?)",("Pengantar Jaringan Komputer","Informatika","XII","Materi pengantar jaringan komputer."))
        au, ap = os.environ.get("INITIAL_ADMIN_USERNAME"), os.environ.get("INITIAL_ADMIN_PASSWORD")
        if au and ap and not c.execute("SELECT 1 FROM users WHERE username=?",(au,)).fetchone():
            c.execute("INSERT INTO users(username,password_hash,role,display_name) VALUES(?,?,?,?)",(au,generate_password_hash(ap),"admin","Administrator Sekolah"))
        c.commit()

def user():
    uid=session.get("uid")
    if not uid: return None
    with conn() as c: return c.execute("SELECT * FROM users WHERE id=? AND active=1",(uid,)).fetchone()

@app.context_processor
def context():
    def csrf():
        if "_csrf" not in session: session["_csrf"]=secrets.token_urlsafe(32)
        return session["_csrf"]
    return {"logged_user":user(),"csrf_token":csrf}

@app.before_request
def protect_posts():
    if request.method=="POST":
        if not session.get("_csrf") or not secrets.compare_digest(session["_csrf"],request.form.get("_csrf_token","")):
            abort(400,"Token keamanan tidak valid. Muat ulang halaman.")

def require(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            u=user()
            if not u:
                flash("Silakan login terlebih dahulu.","error"); return redirect(url_for("login",next=request.path))
            if roles and u["role"] not in roles: abort(403)
            return fn(*a,**kw)
        return wrapped
    return deco

@app.errorhandler(403)
def e403(e): return render_template("error.html",code=403,message="Akun Anda tidak memiliki izin membuka halaman ini."),403
@app.errorhandler(400)
def e400(e): return render_template("error.html",code=400,message=getattr(e,"description","Permintaan tidak valid.")),400

@app.route("/")
def home():
    with conn() as c:
        counts={k:c.execute(q).fetchone()[0] for k,q in {"Siswa":"SELECT COUNT(*) FROM students","Guru":"SELECT COUNT(*) FROM teachers","Materi":"SELECT COUNT(*) FROM materials","Pengumuman":"SELECT COUNT(*) FROM announcements"}.items()}
        news=c.execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 4").fetchall()
    return render_template("home.html",counts=counts,news=news)

@app.route("/profil")
def profil(): return render_template("profil.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if user(): return redirect(url_for("dashboard"))
    if request.method=="POST":
        with conn() as c: u=c.execute("SELECT * FROM users WHERE username=? AND active=1",(request.form.get("username","").strip(),)).fetchone()
        if u and check_password_hash(u["password_hash"],request.form.get("password","")):
            session.clear(); session["uid"]=u["id"]; session["_csrf"]=secrets.token_urlsafe(32)
            dest=request.args.get("next","")
            return redirect(dest if dest.startswith("/") and not dest.startswith("//") else url_for("dashboard"))
        flash("Nama pengguna atau kata sandi salah.","error")
    return render_template("login.html")

@app.route("/logout",methods=["POST"])
@require()
def logout(): session.clear(); flash("Anda sudah keluar.","success"); return redirect(url_for("home"))

@app.route("/dashboard")
@require()
def dashboard():
    u=user()
    with conn() as c:
        if u["role"]=="siswa":
            sid=u["student_id"] or -1
            student=c.execute("SELECT * FROM students WHERE id=?",(sid,)).fetchone()
            grades=c.execute("SELECT * FROM grades WHERE student_id=? ORDER BY id DESC",(sid,)).fetchall()
            att=c.execute("SELECT * FROM attendance WHERE student_id=? ORDER BY attendance_date DESC",(sid,)).fetchall()
            cls=student["class_name"] if student else ""
            materials=c.execute("SELECT * FROM materials WHERE class_name IS NULL OR class_name='' OR class_name=?",(cls,)).fetchall()
            schedules=c.execute("SELECT * FROM schedules WHERE class_name=? ORDER BY day_name,start_time",(cls,)).fetchall()
            return render_template("dashboard.html",u=u,student=student,grades=grades,att=att,materials=materials,schedules=schedules)
        counts={k:c.execute(q).fetchone()[0] for k,q in {"Siswa":"SELECT COUNT(*) FROM students","Guru":"SELECT COUNT(*) FROM teachers","Materi":"SELECT COUNT(*) FROM materials","Pengumuman":"SELECT COUNT(*) FROM announcements"}.items()}
    return render_template("dashboard.html",u=u,counts=counts)

@app.route("/pengumuman",methods=["GET","POST"])
def pengumuman():
    u=user()
    with conn() as c:
        if request.method=="POST":
            if not u or u["role"] not in ("admin","guru"): abort(403)
            title=request.form.get("title","").strip(); body=request.form.get("content","").strip()
            if title and body: c.execute("INSERT INTO announcements(title,content) VALUES(?,?)",(title,body)); c.commit(); flash("Pengumuman disimpan.","success")
            return redirect(url_for("pengumuman"))
        items=c.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    return render_template("pengumuman.html",items=items)

@app.route("/siswa",methods=["GET","POST"])
@require("admin")
def siswa():
    with conn() as c:
        if request.method=="POST":
            name=request.form.get("name","").strip()
            if name:
                c.execute("INSERT INTO students(nis,name,class_name,gender) VALUES(?,?,?,?)",(request.form.get("nis",""),name,request.form.get("class_name",""),request.form.get("gender",""))); c.commit(); flash("Data siswa disimpan.","success")
            return redirect(url_for("siswa"))
        items=c.execute("SELECT * FROM students ORDER BY name").fetchall()
    return render_template("siswa.html",items=items)

@app.route("/guru",methods=["GET","POST"])
@require("admin")
def guru():
    with conn() as c:
        if request.method=="POST":
            name=request.form.get("name","").strip()
            if name: c.execute("INSERT INTO teachers(name,subject,email) VALUES(?,?,?)",(name,request.form.get("subject",""),request.form.get("email",""))); c.commit(); flash("Data guru disimpan.","success")
            return redirect(url_for("guru"))
        items=c.execute("SELECT * FROM teachers ORDER BY name").fetchall()
    return render_template("guru.html",items=items)

@app.route("/akun",methods=["GET","POST"])
@require("admin")
def akun():
    with conn() as c:
        students=c.execute("SELECT * FROM students ORDER BY name").fetchall()
        if request.method=="POST":
            username=request.form.get("username","").strip(); password=request.form.get("password",""); role=request.form.get("role",""); display=request.form.get("display_name","").strip(); sid=request.form.get("student_id") or None
            if len(username)<4 or len(password)<12 or role not in ("admin","guru","siswa") or not display:
                flash("Username minimal 4 karakter, kata sandi minimal 12 karakter, dan isi semua kolom.","error")
            elif role=="siswa" and not sid: flash("Pilih data siswa untuk akun siswa.","error")
            else:
                try:
                    c.execute("INSERT INTO users(username,password_hash,role,display_name,student_id) VALUES(?,?,?,?,?)",(username,generate_password_hash(password),role,display,sid if role=="siswa" else None)); c.commit(); flash("Akun berhasil dibuat.","success")
                except sqlite3.IntegrityError: flash("Username sudah digunakan.","error")
            return redirect(url_for("akun"))
        users=c.execute("SELECT username,role,display_name,active FROM users ORDER BY id DESC").fetchall()
    return render_template("akun.html",students=students,users=users)

@app.route("/absensi",methods=["GET","POST"])
@require("admin","guru","siswa")
def absensi():
    u=user()
    with conn() as c:
        if u["role"]=="siswa":
            items=c.execute("SELECT * FROM attendance WHERE student_id=? ORDER BY attendance_date DESC",(u["student_id"] or -1,)).fetchall()
            return render_template("student_table.html",title="Kehadiran Saya",headers=["Tanggal","Status","Catatan"],rows=[(x["attendance_date"],x["status"],x["notes"]) for x in items])
        if request.method=="POST":
            sid=request.form.get("student_id"); status=request.form.get("status"); d=request.form.get("attendance_date") or str(date.today())
            if sid and status: c.execute("INSERT INTO attendance(student_id,attendance_date,status,notes) VALUES(?,?,?,?)",(sid,d,status,request.form.get("notes",""))); c.commit(); flash("Absensi disimpan.","success")
            return redirect(url_for("absensi"))
        students=c.execute("SELECT * FROM students ORDER BY name").fetchall()
        items=c.execute("SELECT a.*,s.name,s.class_name FROM attendance a JOIN students s ON s.id=a.student_id ORDER BY a.attendance_date DESC LIMIT 100").fetchall()
    return render_template("absensi.html",students=students,items=items,today=str(date.today()))

@app.route("/jadwal",methods=["GET","POST"])
@require("admin","guru","siswa")
def jadwal():
    u=user()
    with conn() as c:
        if request.method=="POST":
            if u["role"]=="siswa": abort(403)
            f=[request.form.get(k,"").strip() for k in ("class_name","day_name","start_time","subject","teacher")]
            if f[0] and f[1] and f[3]: c.execute("INSERT INTO schedules(class_name,day_name,start_time,subject,teacher) VALUES(?,?,?,?,?)",f); c.commit(); flash("Jadwal disimpan.","success")
            return redirect(url_for("jadwal"))
        if u["role"]=="siswa":
            st=c.execute("SELECT class_name FROM students WHERE id=?",(u["student_id"] or -1,)).fetchone(); items=c.execute("SELECT * FROM schedules WHERE class_name=? ORDER BY day_name,start_time",(st["class_name"] if st else "",)).fetchall()
        else: items=c.execute("SELECT * FROM schedules ORDER BY day_name,start_time").fetchall()
    return render_template("jadwal.html",items=items,can_edit=u["role"] in ("admin","guru"))

@app.route("/nilai",methods=["GET","POST"])
@require("admin","guru","siswa")
def nilai():
    u=user()
    with conn() as c:
        if u["role"]=="siswa":
            items=c.execute("SELECT g.*,s.name,s.class_name FROM grades g JOIN students s ON s.id=g.student_id WHERE g.student_id=? ORDER BY g.id DESC",(u["student_id"] or -1,)).fetchall()
            return render_template("nilai_siswa.html",items=items)
        if request.method=="POST":
            try:
                score=float(request.form.get("score",""))
                if not 0<=score<=100: raise ValueError()
                c.execute("INSERT INTO grades(student_id,subject,assessment,score) VALUES(?,?,?,?)",(request.form.get("student_id"),request.form.get("subject",""),request.form.get("assessment",""),score)); c.commit(); flash("Nilai disimpan.","success")
            except (ValueError,TypeError): flash("Nilai harus berupa angka 0–100.","error")
            return redirect(url_for("nilai"))
        students=c.execute("SELECT * FROM students ORDER BY name").fetchall()
        items=c.execute("SELECT g.*,s.name,s.class_name FROM grades g JOIN students s ON s.id=g.student_id ORDER BY g.id DESC LIMIT 200").fetchall()
    return render_template("nilai.html",students=students,items=items)

@app.route("/materi",methods=["GET","POST"])
def materi():
    u=user()
    with conn() as c:
        if request.method=="POST":
            if not u or u["role"] not in ("admin","guru"): abort(403)
            title=request.form.get("title","").strip()
            if title: c.execute("INSERT INTO materials(title,subject,class_name,description,material_url) VALUES(?,?,?,?,?)",(title,request.form.get("subject",""),request.form.get("class_name",""),request.form.get("description",""),request.form.get("material_url",""))); c.commit(); flash("Materi disimpan.","success")
            return redirect(url_for("materi"))
        if u and u["role"]=="siswa":
            st=c.execute("SELECT class_name FROM students WHERE id=?",(u["student_id"] or -1,)).fetchone(); cls=st["class_name"] if st else ""
            items=c.execute("SELECT * FROM materials WHERE class_name IS NULL OR class_name='' OR class_name=? ORDER BY id DESC",(cls,)).fetchall()
        else: items=c.execute("SELECT * FROM materials ORDER BY id DESC").fetchall()
    return render_template("materi.html",items=items,can_manage=bool(u and u["role"] in ("admin","guru")))

@app.route("/ppdb",methods=["GET","POST"])
def ppdb():
    with conn() as c:
        if request.method=="POST":
            name=request.form.get("student_name","").strip()
            if name: c.execute("INSERT INTO ppdb(student_name,parent_name,phone,previous_school) VALUES(?,?,?,?)",(name,request.form.get("parent_name",""),request.form.get("phone",""),request.form.get("previous_school",""))); c.commit(); flash("Formulir minat PPDB dicatat. Ini bukan pendaftaran resmi.","success")
            return redirect(url_for("ppdb"))
        items=c.execute("SELECT * FROM ppdb ORDER BY id DESC").fetchall() if user() and user()["role"]=="admin" else []
    return render_template("ppdb.html",items=items)

if __name__=="__main__":
    init_db()
    app.run(debug=False)
