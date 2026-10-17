import os, sqlite3, time
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput

BG = (0.04, 0.07, 0.10, 1)
GOLD = (0.90, 0.72, 0.22, 1)
Window.clearcolor = BG

def money(n):
    return f"{float(n):,.0f} so'm"

def timer(sec):
    sec = max(0, int(sec))
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"

class BilliardClub(App):
    def build(self):
        self.title = "BILYARD CLUB"
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.db = sqlite3.connect(os.path.join(self.user_data_dir, "club_data.db"))
        self.db.row_factory = sqlite3.Row
        self.page = "home"
        self.current_table = None
        self.init_db()
        self.root_box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        self.show_home()
        Clock.schedule_interval(self.update_visible_timer, 1)
        return self.root_box

    def init_db(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS tables(
          id INTEGER PRIMARY KEY,kind TEXT NOT NULL,number INTEGER NOT NULL,price REAL NOT NULL DEFAULT 30000,
          active INTEGER NOT NULL DEFAULT 0,started REAL,paused INTEGER NOT NULL DEFAULT 0,
          paused_at REAL,paused_seconds INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS products(
          id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'Gazak',
          size TEXT NOT NULL DEFAULT '',price REAL NOT NULL DEFAULT 0,cost REAL NOT NULL DEFAULT 0,
          active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sales(
          id INTEGER PRIMARY KEY AUTOINCREMENT,table_id INTEGER NOT NULL,product_id INTEGER,
          name TEXT NOT NULL,size TEXT NOT NULL DEFAULT '',qty INTEGER NOT NULL DEFAULT 1,
          total REAL NOT NULL DEFAULT 0,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,table_id INTEGER NOT NULL,kind TEXT NOT NULL,
          table_number INTEGER NOT NULL,started REAL NOT NULL,ended REAL NOT NULL,
          seconds INTEGER NOT NULL,total REAL NOT NULL);
        """)
        defaults = {"club_name":"BILYARD CLUB","login_password":"","admin_password":""}
        for k,v in defaults.items():
            self.db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
        for i in range(1,6):
            self.db.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)",(i,"BILLIARD",i,30000))
        for i in range(1,4):
            self.db.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)",(100+i,"TENNIS",i,20000))
        if not self.db.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
            vals = [
                ("Suv","Ichimlik","0.5L",3000,0),("Suv","Ichimlik","1L",5000,0),
                ("Suv","Ichimlik","1.5L",7000,0),("Suv","Ichimlik","2L",9000,0),
            ]
            for name in ("Coca-Cola","Fanta","Sprite","Pepsi"):
                vals += [(name,"Ichimlik",sz,p,0) for sz,p in [("0.5L",7000),("1L",11000),("1.5L",15000),("2L",19000)]]
            vals += [("Chips","Gazak","",10000,4000),("Suxarik","Gazak","",8000,3000),
                     ("Shokolad","Gazak","",10000,5000),("Yong'oq","Gazak","",15000,8000),
                     ("Pullik tayoqcha","Tayoqcha","",5000,0)]
            self.db.executemany("INSERT INTO products(name,category,size,price,cost) VALUES(?,?,?,?,?)", vals)
        self.db.commit()

    def setting(self, key):
        r = self.db.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
        return r["value"] if r else ""

    def set_setting(self,key,value):
        self.db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(key,str(value)))
        self.db.commit()

    def clear(self):
        self.root_box.clear_widgets()

    def lbl(self, text, size=16, height=42, color=(1,1,1,1)):
        return Label(text=str(text), size_hint_y=None, height=dp(height), font_size=dp(size),
                     color=color, halign="center", valign="middle")

    def button(self, text, fn, height=48):
        b = Button(text=text, size_hint_y=None, height=dp(height), font_size=dp(15),
                   background_normal="", background_color=(0.10,0.28,0.39,1), color=(1,1,1,1))
        b.bind(on_release=lambda *_: fn())
        return b

    def heading(self, title):
        self.root_box.add_widget(self.lbl(title, 23, 54, GOLD))

    def popup(self, title, message, height=180):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        box.add_widget(self.lbl(message, 16, height-60))
        box.add_widget(self.button("YOPISH", lambda: pop.dismiss()))
        pop = Popup(title=title, content=box, size_hint=(.9,None), height=dp(height))
        pop.open()

    def elapsed(self, row):
        if not row["active"] or row["started"] is None:
            return 0
        end = row["paused_at"] if row["paused"] and row["paused_at"] else time.time()
        return max(0, int(end - row["started"] - (row["paused_seconds"] or 0)))

    def show_home(self):
        self.page = "home"
        self.current_table = None
        self.clear()
        self.heading(self.setting("club_name") or "BILYARD CLUB")
        self.root_box.add_widget(self.lbl("Stolni tanlang", 16, 30))
        sc = ScrollView()
        grid = GridLayout(cols=2, spacing=dp(7), padding=dp(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for r in self.db.execute("SELECT * FROM tables ORDER BY id").fetchall():
            status = "⏸ PAUZA" if r["paused"] else ("🔴 BAND" if r["active"] else "🟢 BO'SH")
            kind = "🎱 BILYARD" if r["kind"] == "BILLIARD" else "🏓 TENNIS"
            text = f"{kind} {r['number']}\\n{status}\\n{timer(self.elapsed(r))}\\n{money(r['price'])}/soat"
            grid.add_widget(self.button(text, lambda tid=r["id"]: self.show_table(tid), 110))
        sc.add_widget(grid)
        self.root_box.add_widget(sc)
        nav = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
        nav.add_widget(self.button("MENYU", self.show_menu))
        nav.add_widget(self.button("HISOBOT", self.show_report))
        nav.add_widget(self.button("SOZLAMALAR", self.show_settings))
        self.root_box.add_widget(nav)

    def show_table(self, tid):
        self.page = "table"
        self.current_table = tid
        r = self.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
        self.clear()
        self.heading(f"{r['kind']} {r['number']}")
        timer_label = self.lbl(timer(self.elapsed(r)), 31, 68, GOLD)
        self.timer_label = timer_label
        self.root_box.add_widget(timer_label)
        self.root_box.add_widget(self.lbl(f"Stol narxi: {money(r['price'])} / soat", 16, 40))
        if not r["active"]:
            self.root_box.add_widget(self.button("▶ BAND QILISH / BOSHLASH", lambda: self.start_table(tid), 54))
        else:
            self.root_box.add_widget(self.button("▶ DAVOM ETTIRISH" if r["paused"] else "⏸ PAUZA",
                                                  lambda: self.toggle_pause(tid), 52))
            self.root_box.add_widget(self.button("🥤 MAHSULOT QO'SHISH", lambda: self.show_menu(tid), 52))
            self.root_box.add_widget(self.button("⏹ TUGATISH VA CHEK", lambda: self.finish_table(tid), 52))
            sales = self.db.execute("SELECT name,size,qty,total FROM sales WHERE table_id=? AND created>=? ORDER BY id",
                                    (tid,r["started"] or 0)).fetchall()
            self.root_box.add_widget(self.lbl("Stolga qo'shilgan mahsulotlar", 15, 35, GOLD))
            sc = ScrollView()
            items = GridLayout(cols=1, size_hint_y=None, spacing=dp(3))
            items.bind(minimum_height=items.setter("height"))
            for s in sales:
                items.add_widget(self.lbl(f"{s['name']} {s['size']} ×{s['qty']} — {money(s['total'])}",14,34))
            sc.add_widget(items)
            self.root_box.add_widget(sc)
        self.root_box.add_widget(self.button("ORTGA", self.show_home))

    def start_table(self, tid):
        self.db.execute("UPDATE tables SET active=1,started=?,paused=0,paused_at=NULL,paused_seconds=0 WHERE id=?",
                        (time.time(),tid))
        self.db.commit()
        self.show_table(tid)

    def toggle_pause(self, tid):
        r = self.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
        now = time.time()
        if not r["paused"]:
            self.db.execute("UPDATE tables SET paused=1,paused_at=? WHERE id=?",(now,tid))
        else:
            extra = max(0,int(now-(r["paused_at"] or now)))
            self.db.execute("UPDATE tables SET paused=0,paused_at=NULL,paused_seconds=paused_seconds+? WHERE id=?",(extra,tid))
        self.db.commit()
        self.show_table(tid)

    def finish_table(self, tid):
        r = self.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
        sec = self.elapsed(r)
        table_total = sec / 3600 * r["price"]
        sales_total = self.db.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE table_id=? AND created>=?",
                                      (tid,r["started"] or 0)).fetchone()[0]
        ended = time.time()
        self.db.execute("INSERT INTO sessions(table_id,kind,table_number,started,ended,seconds,total) VALUES(?,?,?,?,?,?,?)",
                        (tid,r["kind"],r["number"],r["started"] or ended,ended,sec,table_total))
        self.db.execute("UPDATE tables SET active=0,started=NULL,paused=0,paused_at=NULL,paused_seconds=0 WHERE id=?",(tid,))
        self.db.commit()
        self.popup("CHEK", f"{r['kind']} {r['number']}\\nVaqt: {timer(sec)}\\nStol: {money(table_total)}\\nMahsulotlar: {money(sales_total)}\\nJAMI: {money(table_total+sales_total)}", 250)
        self.show_home()

    def show_menu(self, tid=None):
        self.page = "menu"
        self.clear()
        self.heading("MENYU")
        if tid is not None:
            self.root_box.add_widget(self.lbl("Mahsulotni bosib stolga qo'shing",14,32))
        sc = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(5), padding=dp(3), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        products = self.db.execute("SELECT * FROM products WHERE active=1 ORDER BY category,name,size").fetchall()
        for p in products:
            label = f"{p['name']} {p['size']} — {money(p['price'])}"
            def choose(prod=p):
                if tid is None:
                    self.popup("MENYU", "Mahsulotni sotish uchun faol stol ichidan menyuni oching.", 150)
                    return
                row = self.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
                if not row or not row["active"]:
                    self.popup("STOL", "Avval stolni band qiling.", 150)
                    return
                self.db.execute("INSERT INTO sales(table_id,product_id,name,size,qty,total,created) VALUES(?,?,?,?,?,?,?)",
                                (tid,prod["id"],prod["name"],prod["size"],1,prod["price"],time.time()))
                self.db.commit()
                self.show_table(tid)
            grid.add_widget(self.button(label, choose, 48))
        sc.add_widget(grid)
        self.root_box.add_widget(sc)
        self.root_box.add_widget(self.button("ORTGA", lambda: self.show_table(tid) if tid else self.show_home()))

    def show_report(self):
        self.page = "report"
        self.clear()
        self.heading("HISOBOT")
        day = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        table_sum = self.db.execute("SELECT COALESCE(SUM(total),0) FROM sessions WHERE ended>=?",(day,)).fetchone()[0]
        sales_sum = self.db.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE created>=?",(day,)).fetchone()[0]
        count_b = self.db.execute("SELECT COUNT(*) FROM sessions WHERE kind='BILLIARD' AND ended>=?",(day,)).fetchone()[0]
        count_t = self.db.execute("SELECT COUNT(*) FROM sessions WHERE kind='TENNIS' AND ended>=?",(day,)).fetchone()[0]
        for line in [f"Bugungi stol tushumi: {money(table_sum)}",f"Bugungi mahsulot tushumi: {money(sales_sum)}",
                     f"JAMI: {money(table_sum+sales_sum)}",f"Bilyard seanslari: {count_b}",f"Tennis seanslari: {count_t}"]:
            self.root_box.add_widget(self.lbl(line,17,48))
        self.root_box.add_widget(self.button("ORTGA",self.show_home))

    def ask_text(self, title, prompt, initial="", callback=None, password=False):
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        box.add_widget(self.lbl(prompt,15,38))
        inp = TextInput(text=str(initial), multiline=False, password=password, size_hint_y=None, height=dp(45))
        box.add_widget(inp)
        pop = Popup(title=title, content=box, size_hint=(.9,None), height=dp(220))
        def save():
            value = inp.text.strip()
            pop.dismiss()
            if callback:
                callback(value)
        box.add_widget(self.button("SAQLASH",save))
        pop.open()

    def admin_ok(self, action):
        password = self.setting("admin_password")
        if not password:
            self.popup("ADMIN", "Avval Sozlamalar ichida admin parolini yarating.", 160)
            return
        self.ask_text("ADMIN", "Admin paroli:", callback=lambda val: action() if val == password else self.popup("XATO","Parol noto'g'ri.",130), password=True)

    def show_settings(self):
        self.page = "settings"
        self.clear()
        self.heading("SOZLAMALAR")
        self.root_box.add_widget(self.button("KLUB NOMINI O'ZGARTIRISH", lambda: self.ask_text("Klub nomi","Yangi nom:",self.setting("club_name"),lambda v:(self.set_setting("club_name",v),self.show_settings())),50))
        self.root_box.add_widget(self.button("KIRISH PAROLINI O'RNATISH", lambda: self.ask_text("Kirish paroli","Yangi parol (bo'sh qoldirsangiz parolsiz):",callback=lambda v:(self.set_setting("login_password",v),self.popup("TAYYOR","Kirish paroli saqlandi."))),50))
        self.root_box.add_widget(self.button("ADMIN PAROLINI O'RNATISH", lambda: self.ask_text("Admin paroli","Yangi admin paroli:",callback=lambda v:(self.set_setting("admin_password",v),self.popup("TAYYOR","Admin paroli saqlandi."))),50))
        self.root_box.add_widget(self.lbl("Stol narxlari",16,35,GOLD))
        sc = ScrollView()
        items = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        items.bind(minimum_height=items.setter("height"))
        for r in self.db.execute("SELECT * FROM tables ORDER BY id").fetchall():
            items.add_widget(self.button(f"{r['kind']} {r['number']} — {money(r['price'])}",lambda tid=r["id"],p=r["price"]: self.ask_text("Stol narxi","Yangi narx:",p,lambda v:self.set_price(tid,v)),44))
        sc.add_widget(items)
        self.root_box.add_widget(sc)
        self.root_box.add_widget(self.button("MAHSULOT QO'SHISH",lambda:self.admin_ok(self.add_product_form),48))
        self.root_box.add_widget(self.button("ORTGA",self.show_home))

    def set_price(self, tid, value):
        try:
            self.db.execute("UPDATE tables SET price=? WHERE id=?",(float(value),tid))
            self.db.commit()
            self.show_settings()
        except Exception:
            self.popup("XATO","Narxni raqam bilan kiriting.",130)

    def add_product_form(self):
        def got_name(name):
            if not name:
                return
            self.ask_text("Mahsulot","Narxi (so'm):","0",lambda p: self.save_product(name,p))
        self.ask_text("Mahsulot","Mahsulot nomi:",callback=got_name)

    def save_product(self,name,price):
        try:
            self.db.execute("INSERT INTO products(name,category,size,price,cost,active) VALUES(?,?,?,?,0,1)",(name,"Gazak","",float(price)))
            self.db.commit()
            self.show_settings()
        except Exception:
            self.popup("XATO","Mahsulot yoki narxni tekshiring.",130)

    def update_visible_timer(self, _dt):
        if self.page == "table" and self.current_table is not None and hasattr(self,"timer_label"):
            row = self.db.execute("SELECT * FROM tables WHERE id=?",(self.current_table,)).fetchone()
            if row:
                self.timer_label.text = timer(self.elapsed(row))
        elif self.page == "home":
            self.show_home()

    def on_stop(self):
        if hasattr(self,"db"):
            self.db.commit()
            self.db.close()

if __name__ == "__main__":
    BilliardClub().run()
