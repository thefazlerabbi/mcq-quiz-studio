
import os
import json
import random
import hashlib
from datetime import datetime
from collections import Counter, defaultdict

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.filechooser import FileChooserListView

APP_NAME = "MCQ Quiz Studio"
ACCENT = (0.10, 0.42, 0.42, 1)       # muted teal
ACCENT_DARK = (0.07, 0.30, 0.31, 1)
BG = (0.95, 0.965, 0.955, 1)         # soft off-white
CARD = (1, 1, 1, 1)
TEXT = (0.12, 0.16, 0.17, 1)
MUTED = (0.38, 0.43, 0.43, 1)
GOOD = (0.20, 0.52, 0.38, 1)
BAD = (0.72, 0.32, 0.30, 1)
SOFT_GOOD = (0.90, 0.96, 0.92, 1)
SOFT_BAD = (0.97, 0.91, 0.91, 1)

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def qid_for(q):
    base = str(q.get("source_no","")) + "|" + q["question"].strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

def normalize_header(x):
    return re.sub(r"[^a-z0-9]+", "", str(x or "").strip().lower())

def make_card(widget, radius=12, color=CARD, border=None):
    with widget.canvas.before:
        Color(*color)
        widget._bg = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)]*4)
        if border:
            Color(*border)
            widget._line = Line(rounded_rectangle=(widget.x, widget.y, widget.width, widget.height, dp(radius)), width=1)
    def update(*_):
        widget._bg.pos = widget.pos
        widget._bg.size = widget.size
        if hasattr(widget, "_line"):
            widget._line.rounded_rectangle = (widget.x, widget.y, widget.width, widget.height, dp(radius))
    widget.bind(pos=update, size=update)
    return widget

class AdaptiveLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.bind(size=self._sync)
    def _sync(self, *_):
        self.text_size = (max(0, self.width - dp(8)), None)

class PrimaryButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", ACCENT)
        kwargs.setdefault("color", (1,1,1,1))
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(48))
        kwargs.setdefault("bold", True)
        super().__init__(**kwargs)

class SoftButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0.91,0.94,0.93,1))
        kwargs.setdefault("color", ACCENT_DARK)
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(46))
        super().__init__(**kwargs)

class MCQApp(App):
    bank = []
    history = {}
    bookmarks = set()
    current_bank_key = ""
    mode = "practice"
    quiz_questions = []
    quiz_index = 0
    answered = False
    selected_letter = None
    score = 0
    wrong = 0
    skipped = 0
    started_at = None
    timer_seconds = 0
    timer_event = None
    session_answers = {}
    setup_total = 0
    current_file_name = ""

    def build(self):
        self.title = APP_NAME
        self.root = BoxLayout(orientation="vertical", spacing=0)
        self.load_history()
        self.show_home()
        return self.root

    def content(self):
        sv = ScrollView(do_scroll_x=False)
        box = BoxLayout(orientation="vertical", padding=[dp(14),dp(12)], spacing=dp(12), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        sv.add_widget(box)
        self.root.clear_widgets()
        self.root.add_widget(sv)
        return box

    def header(self, title, subtitle=""):
        row = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(10))
        lab = AdaptiveLabel(text=title, font_size=sp(21), bold=True, color=TEXT, size_hint_x=1)
        row.add_widget(lab)
        if subtitle:
            s = AdaptiveLabel(text=subtitle, font_size=sp(12), color=MUTED, size_hint_x=None, width=dp(100))
            row.add_widget(s)
        return row

    def card_label(self, text, size=15, bold=False, color=TEXT, min_h=50):
        w = AdaptiveLabel(text=text, font_size=sp(size), bold=bold, color=color,
                          size_hint_y=None, padding=[dp(12),dp(10)])
        w.bind(texture_size=lambda inst, val: setattr(inst, "height", max(dp(min_h), val[1]+dp(20))))
        make_card(w, color=CARD, border=(0.86,0.89,0.88,1))
        return w

    def show_home(self):
        self.stop_timer()
        box = self.content()
        box.add_widget(self.header(APP_NAME, "Study • Practice • Track"))
        if self.bank:
            summary = f"{self.current_file_name}\n{len(self.bank)} MCQs ready"
            box.add_widget(self.card_label(summary, 17, True, ACCENT_DARK, 72))
            box.add_widget(PrimaryButton(text="START QUIZ", on_release=lambda *_: self.show_setup()))
            box.add_widget(SoftButton(text="DASHBOARD", on_release=lambda *_: self.show_dashboard()))
            box.add_widget(SoftButton(text="QUESTION BANK", on_release=lambda *_: self.show_bank_manager()))
        else:
            box.add_widget(self.card_label(
                "Select an Excel (.xlsx) file. The app will detect Question, A, B, C, D and Correct columns automatically.",
                15, False, TEXT, 90))
            box.add_widget(PrimaryButton(text="SELECT EXCEL FILE", on_release=lambda *_: self.pick_excel()))
            box.add_widget(SoftButton(text="HOW IT WORKS", on_release=lambda *_: self.show_help()))
        box.add_widget(SoftButton(text="SETTINGS / HELP", on_release=lambda *_: self.show_help()))
        box.add_widget(AdaptiveLabel(text="Clean UI • Eye-friendly • Offline progress", font_size=sp(12),
                                     color=MUTED, size_hint_y=None, height=dp(30)))

    def show_help(self):
        box = self.content()
        box.add_widget(self.header("How it works"))
        text = (
            "1. Select any .xlsx MCQ file.\n"
            "2. The first row is treated as headers.\n"
            "3. Required columns: Question, A, B, C, D and Correct.\n"
            "4. Correct may be A/B/C/D or the exact answer text.\n"
            "5. Optional columns: No, Section, Difficulty.\n"
            "6. Choose a range, section, mode and question count.\n"
            "7. Progress is saved locally on the phone.\n\n"
            "Practice: instant feedback.\n"
            "Exam: answers are revealed at the end.\n"
            "Smart: gives more weight to weak/unseen questions."
        )
        box.add_widget(self.card_label(text, 15, False, TEXT, 260))
        box.add_widget(SoftButton(text="BACK", on_release=lambda *_: self.show_home()))

    def pick_excel(self):
        # Android: use the system document picker through pyjnius.
        try:
            from jnius import autoclass, cast
            from android import activity
            Intent = autoclass("android.content.Intent")
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            activity.bind(on_activity_result=self.on_android_file)
            activity.startActivityForResult(intent, 9001)
        except Exception:
            # Desktop fallback for testing.
            self.desktop_pick_excel()

    def on_android_file(self, request_code, result_code, intent):
        if request_code != 9001 or result_code != -1 or intent is None:
            return
        try:
            uri = intent.getData()
            self.import_android_uri(uri)
        except Exception as e:
            self.popup("Import error", str(e))

    def import_android_uri(self, uri):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            resolver = activity.getContentResolver()
            stream = resolver.openInputStream(uri)
            name = self.get_display_name(resolver, uri) or "question_bank.xlsx"
            safe = re.sub(r"[^A-Za-z0-9._ -]+", "_", name)
            dest = os.path.join(self.user_data_dir, safe)
            with open(dest, "wb") as f:
                buf = bytearray(32768)
                while True:
                    n = stream.read(buf)
                    if n == -1:
                        break
                    if n > 0:
                        f.write(bytes(buf[:n]))
            stream.close()
            self.load_excel(dest)
        except Exception as e:
            self.popup("Could not import Excel", str(e))

    def get_display_name(self, resolver, uri):
        try:
            from jnius import autoclass
            OpenableColumns = autoclass("android.provider.OpenableColumns")
            cursor = resolver.query(uri, None, None, None, None)
            if cursor and cursor.moveToFirst():
                idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                name = cursor.getString(idx) if idx >= 0 else None
                cursor.close()
                return name
        except Exception:
            pass
        return None

    def desktop_pick_excel(self):
        chooser = FileChooserListView(filters=["*.xlsx"], path=os.getcwd())
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(chooser)
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        p = PrimaryButton(text="OPEN")
        c = SoftButton(text="CANCEL")
        buttons.add_widget(p); buttons.add_widget(c); box.add_widget(buttons)
        pop = Popup(title="Select Excel", content=box, size_hint=(.94,.86))
        p.bind(on_release=lambda *_: (pop.dismiss(), self.load_excel(chooser.selection[0]) if chooser.selection else None))
        c.bind(on_release=pop.dismiss)
        pop.open()

    def load_excel(self, path):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                raise ValueError("Excel is empty.")
            headers = [normalize_header(x) for x in rows[0]]
            def idx(*names):
                for n in names:
                    if normalize_header(n) in headers:
                        return headers.index(normalize_header(n))
                return -1
            iq = idx("question", "questions", "mcq", "questiontext")
            ia, ib, ic, idd = idx("a"), idx("b"), idx("c"), idx("d")
            icr = idx("correct", "answer", "correctanswer")
            ino = idx("no", "number", "qno", "questionno")
            isec = idx("section", "category", "topic")
            idiff = idx("difficulty", "level")
            missing = []
            if iq < 0: missing.append("Question")
            if ia < 0 or ib < 0 or ic < 0 or idd < 0: missing.append("A/B/C/D")
            if icr < 0: missing.append("Correct")
            if missing:
                raise ValueError("Missing required column(s): " + ", ".join(missing))
            bank = []
            for rnum, row in enumerate(rows[1:], start=2):
                def cell(i):
                    return "" if i < 0 or i >= len(row) or row[i] is None else str(row[i]).strip()
                qtext = cell(iq)
                opts = [cell(ia), cell(ib), cell(ic), cell(idd)]
                corr = cell(icr)
                if not qtext or any(not x for x in opts) or not corr:
                    continue
                letter = None
                if corr.upper() in ("A","B","C","D"):
                    letter = corr.upper()
                else:
                    for j, op in enumerate(opts):
                        if corr.strip().casefold() == op.strip().casefold():
                            letter = "ABCD"[j]
                            break
                if not letter:
                    continue
                q = {
                    "row": rnum,
                    "source_no": cell(ino) if ino >= 0 else str(rnum-1),
                    "section": cell(isec) if isec >= 0 else "Uncategorized",
                    "difficulty": cell(idiff) if idiff >= 0 else "Unrated",
                    "question": qtext,
                    "options": {"A":opts[0],"B":opts[1],"C":opts[2],"D":opts[3]},
                    "correct": letter,
                }
                q["id"] = qid_for(q)
                bank.append(q)
            wb.close()
            if not bank:
                raise ValueError("No valid MCQs found.")
            self.bank = bank
            self.current_file_name = os.path.basename(path)
            self.current_bank_key = hashlib.sha1(
                ("|".join(q["id"] for q in bank)).encode("utf-8")
            ).hexdigest()
            self.history.setdefault(self.current_bank_key, {})
            self.bookmarks = set(self.history[self.current_bank_key].get("_bookmarks", []))
            self.save_history()
            self.show_home()
        except Exception as e:
            self.popup("Excel error", str(e))

    def show_setup(self):
        box = self.content()
        box.add_widget(self.header("Quiz Setup", f"Total: {len(self.bank)}"))
        box.add_widget(self.card_label(f"TOTAL MCQs\n{len(self.bank)}", 20, True, ACCENT_DARK, 74))

        # Range
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.from_input = TextInput(text="1", input_filter="int", multiline=False, font_size=sp(16),
                                    size_hint_x=.5, hint_text="From")
        self.to_input = TextInput(text=str(len(self.bank)), input_filter="int", multiline=False,
                                  font_size=sp(16), size_hint_x=.5, hint_text="To")
        row.add_widget(self.from_input); row.add_widget(self.to_input)
        box.add_widget(AdaptiveLabel(text="QUESTION RANGE  (Excel question order)", bold=True,
                                     color=MUTED, size_hint_y=None, height=dp(28)))
        box.add_widget(row)

        sections = sorted(set(q["section"] for q in self.bank))
        self.section_spinner = Spinner(text="All Sections", values=["All Sections"] + sections,
                                       size_hint_y=None, height=dp(48), font_size=sp(15))
        box.add_widget(self.section_spinner)

        self.count_input = TextInput(text=str(min(20,len(self.bank))), input_filter="int",
                                     multiline=False, font_size=sp(16), size_hint_y=None, height=dp(48),
                                     hint_text="Number of questions")
        box.add_widget(AdaptiveLabel(text="NUMBER OF QUESTIONS", bold=True, color=MUTED,
                                     size_hint_y=None, height=dp(28)))
        box.add_widget(self.count_input)

        self.mode_spinner = Spinner(text="Practice", values=["Practice","Exam","Smart"],
                                    size_hint_y=None, height=dp(48), font_size=sp(15))
        box.add_widget(self.mode_spinner)

        self.timer_spinner = Spinner(text="No Timer", values=["No Timer","5 min","10 min","20 min","30 min"],
                                     size_hint_y=None, height=dp(48), font_size=sp(15))
        box.add_widget(self.timer_spinner)

        box.add_widget(SoftButton(text="START — SHUFFLE QUESTIONS", on_release=lambda *_: self.start_quiz(True)))
        box.add_widget(SoftButton(text="START — KEEP ORDER", on_release=lambda *_: self.start_quiz(False)))
        box.add_widget(SoftButton(text="WRONG / WEAK PRACTICE", on_release=lambda *_: self.show_filter_setup()))
        box.add_widget(SoftButton(text="BACK", on_release=lambda *_: self.show_home()))

    def show_filter_setup(self):
        box = self.content()
        box.add_widget(self.header("Targeted Practice"))
        self.filter_spinner = Spinner(text="Wrong Questions", values=[
            "Wrong Questions","Repeated Wrong (3+)","Weak (<70%)","Unseen","Mastered","Bookmarked"
        ], size_hint_y=None, height=dp(48), font_size=sp(15))
        box.add_widget(self.filter_spinner)
        self.count_input2 = TextInput(text="20", input_filter="int", multiline=False,
                                      font_size=sp(16), size_hint_y=None, height=dp(48))
        box.add_widget(self.count_input2)
        box.add_widget(PrimaryButton(text="START TARGETED QUIZ", on_release=lambda *_: self.start_targeted()))
        box.add_widget(SoftButton(text="BACK", on_release=lambda *_: self.show_setup()))

    def stats(self, q):
        st = self.history[self.current_bank_key].get(q["id"], {})
        a = int(st.get("attempts",0)); c = int(st.get("correct",0)); w = int(st.get("wrong",0))
        return a,c,w,(c/a*100 if a else 0)

    def start_targeted(self):
        kind = self.filter_spinner.text
        pool = []
        for q in self.bank:
            a,c,w,acc = self.stats(q)
            if kind == "Wrong Questions" and w > 0: pool.append(q)
            elif kind == "Repeated Wrong (3+)" and w >= 3: pool.append(q)
            elif kind == "Weak (<70%)" and w > 0 and acc < 70: pool.append(q)
            elif kind == "Unseen" and a == 0: pool.append(q)
            elif kind == "Mastered" and a >= 3 and acc >= 90: pool.append(q)
            elif kind == "Bookmarked" and q["id"] in self.bookmarks: pool.append(q)
        if not pool:
            self.popup("No questions", f"No questions currently match: {kind}")
            return
        try: n = max(1, min(int(self.count_input2.text or "20"), len(pool)))
        except: n = min(20,len(pool))
        random.shuffle(pool)
        self.mode = "practice"
        self.quiz_questions = pool[:n]
        self.begin_quiz()

    def start_quiz(self, shuffle=True):
        try:
            lo = int(self.from_input.text or "1")
            hi = int(self.to_input.text or str(len(self.bank)))
            n = int(self.count_input.text or "1")
        except:
            self.popup("Invalid setup", "Use valid numbers.")
            return
        lo = max(1, min(lo, len(self.bank))); hi = max(lo, min(hi, len(self.bank)))
        pool = self.bank[lo-1:hi]
        if self.section_spinner.text != "All Sections":
            pool = [q for q in pool if q["section"] == self.section_spinner.text]
        if not pool:
            self.popup("No questions", "That range/section has no questions.")
            return
        n = max(1, min(n, len(pool)))
        self.mode = self.mode_spinner.text.lower()
        if self.mode == "smart":
            # Weighted without replacement: wrong/weak/unseen receive more weight.
            scored = []
            for q in pool:
                a,c,w,acc = self.stats(q)
                weight = 1.0 + w*2.0 + max(0, 70-acc)/15.0 + (2.0 if a==0 else 0)
                scored.append((q, weight))
            chosen = []
            remaining = scored[:]
            while remaining and len(chosen) < n:
                total = sum(x[1] for x in remaining)
                r = random.random()*total
                s = 0
                pick_i = 0
                for i,(q,w) in enumerate(remaining):
                    s += w
                    if s >= r:
                        pick_i = i; break
                chosen.append(remaining.pop(pick_i)[0])
            self.quiz_questions = chosen
        else:
            if shuffle: random.shuffle(pool)
            self.quiz_questions = pool[:n]
        self.begin_quiz()

    def begin_quiz(self):
        self.quiz_index = 0
        self.answered = False
        self.selected_letter = None
        self.score = self.wrong = self.skipped = 0
        self.started_at = now_iso()
        self.session_answers = {}
        timer_map = {"5 min":300,"10 min":600,"20 min":1200,"30 min":1800}
        self.timer_seconds = timer_map.get(getattr(self,"timer_spinner",None).text if hasattr(self,"timer_spinner") else "No Timer",0)
        self.start_timer()
        self.show_question()

    def start_timer(self):
        self.stop_timer()
        if self.timer_seconds > 0:
            self.timer_event = Clock.schedule_interval(self.tick_timer, 1)

    def stop_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

    def tick_timer(self, dt):
        self.timer_seconds -= 1
        if self.timer_seconds <= 0:
            self.timer_seconds = 0
            self.stop_timer()
            self.finish_quiz(time_up=True)
        elif hasattr(self,"timer_label"):
            self.timer_label.text = self.format_time(self.timer_seconds)

    def format_time(self,s):
        return f"{s//60:02d}:{s%60:02d}"

    def show_question(self):
        q = self.quiz_questions[self.quiz_index]
        box = self.content()
        top = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        top.add_widget(AdaptiveLabel(text=f"Question {self.quiz_index+1} / {len(self.quiz_questions)}",
                                     font_size=sp(19), bold=True))
        self.timer_label = AdaptiveLabel(text=self.format_time(self.timer_seconds) if self.timer_seconds else "",
                                         color=ACCENT_DARK, bold=True, halign="right", size_hint_x=None, width=dp(75))
        top.add_widget(self.timer_label)
        box.add_widget(top)
        a,c,w,acc = self.stats(q)
        box.add_widget(AdaptiveLabel(text=f"History: {a} attempts • {w} wrong • {acc:.0f}% accuracy",
                                     color=MUTED, font_size=sp(13), size_hint_y=None, height=dp(28)))
        qcard = self.card_label(q["question"], 18, True, TEXT, 90)
        box.add_widget(qcard)
        meta = f"Excel No: {q['source_no']}   •   {q['section']}   •   {q['difficulty']}"
        box.add_widget(AdaptiveLabel(text=meta, color=MUTED, font_size=sp(12), size_hint_y=None, height=dp(28)))

        grid = GridLayout(cols=1, spacing=dp(9), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        letters = list("ABCD")
        opts = q["options"].copy()
        items = list(opts.items())
        random.shuffle(items)  # option order is randomized each question
        for letter, text in items:
            b = Button(text=f"{letter}. {text}", size_hint_y=None, height=dp(66),
                       font_size=sp(15), bold=True, halign="left", valign="middle",
                       background_normal="", background_down="", background_color=CARD, color=TEXT)
            b.text_size = (None, None)
            b.bind(size=lambda inst, val: setattr(inst, "text_size", (max(dp(20), inst.width-dp(28)), None)))
            make_card(b, radius=10, color=CARD, border=(0.84,0.88,0.87,1))
            b.bind(on_release=lambda inst, L=letter: self.answer(L, q, grid))
            grid.add_widget(b)
        box.add_widget(grid)
        bottom = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        star = "★ BOOKMARKED" if q["id"] in self.bookmarks else "☆ BOOKMARK"
        bm = SoftButton(text=star, size_hint_x=.48, on_release=lambda *_: self.toggle_bookmark(q))
        bottom.add_widget(bm)
        skip = SoftButton(text="SKIP", size_hint_x=.24, on_release=lambda *_: self.skip_question())
        skip.disabled = self.mode == "exam" and False
        bottom.add_widget(skip)
        box.add_widget(bottom)
        self.next_btn = PrimaryButton(text="NEXT →", disabled=True, on_release=lambda *_: self.next_question())
        box.add_widget(self.next_btn)
        self.feedback = AdaptiveLabel(text="", font_size=sp(15), bold=True, size_hint_y=None, height=dp(46))
        box.add_widget(self.feedback)

    def answer(self, letter, q, grid):
        if self.answered: return
        self.answered = True
        self.selected_letter = letter
        correct = letter == q["correct"]
        self.session_answers[q["id"]] = {"answer":letter,"correct":correct}
        if self.mode == "practice":
            if correct:
                self.score += 1
                self.feedback.text = "✓ RIGHT"
                self.feedback.color = GOOD
            else:
                self.wrong += 1
                self.feedback.text = f"✕ WRONG  •  Correct answer: {q['correct']}"
                self.feedback.color = BAD
        else:
            # Exam and Smart are both end-review modes.
            if correct: self.score += 1
            else: self.wrong += 1
            self.feedback.text = "Answer saved."
            self.feedback.color = MUTED
        self.record(q, letter, correct)
        for child in grid.children:
            child.disabled = True
            if child.text.startswith(f"{letter}."):
                child.background_color = SOFT_GOOD if correct else SOFT_BAD
        self.next_btn.disabled = False
        self.save_history()

    def skip_question(self):
        if self.answered: return
        q = self.quiz_questions[self.quiz_index]
        self.skipped += 1
        self.session_answers[q["id"]] = {"answer":None,"correct":False}
        self.next_question()

    def next_question(self):
        if self.quiz_index >= len(self.quiz_questions)-1:
            self.finish_quiz()
            return
        self.quiz_index += 1
        self.answered = False
        self.selected_letter = None
        self.show_question()

    def finish_quiz(self, time_up=False):
        self.stop_timer()
        box = self.content()
        total = len(self.quiz_questions)
        pct = (self.score/total*100) if total else 0
        box.add_widget(self.header("Quiz Result"))
        msg = f"{'TIME UP\n' if time_up else ''}{self.score} / {total}\n{pct:.1f}% accuracy"
        box.add_widget(self.card_label(msg, 24, True, ACCENT_DARK, 110))
        box.add_widget(self.card_label(
            f"Correct: {self.score}\nWrong: {self.wrong}\nSkipped: {self.skipped}",
            16, False, TEXT, 90))
        box.add_widget(PrimaryButton(text="REVIEW WRONG", on_release=lambda *_: self.review_session_wrong()))
        box.add_widget(SoftButton(text="DASHBOARD", on_release=lambda *_: self.show_dashboard()))
        box.add_widget(SoftButton(text="BACK HOME", on_release=lambda *_: self.show_home()))

    def review_session_wrong(self):
        wrong_ids = [qid for qid,v in self.session_answers.items() if not v.get("correct")]
        pool = [q for q in self.bank if q["id"] in wrong_ids]
        if not pool:
            self.popup("No wrong answers", "There are no wrong answers to review.")
            return
        self.mode = "practice"; self.quiz_questions = pool; self.begin_quiz()

    def record(self,q,letter,correct):
        st = self.history[self.current_bank_key].setdefault(q["id"], {})
        st["attempts"] = int(st.get("attempts",0))+1
        if correct: st["correct"] = int(st.get("correct",0))+1
        else: st["wrong"] = int(st.get("wrong",0))+1
        st["last_answer"] = letter
        st["last_result"] = bool(correct)
        st["last_seen"] = now_iso()
        st["question"] = q["question"]
        st["source_no"] = q["source_no"]

    def toggle_bookmark(self,q):
        if q["id"] in self.bookmarks: self.bookmarks.remove(q["id"])
        else: self.bookmarks.add(q["id"])
        self.history[self.current_bank_key]["_bookmarks"] = list(self.bookmarks)
        self.save_history()
        self.show_question()

    def show_dashboard(self):
        box = self.content()
        box.add_widget(self.header("Dashboard", self.current_file_name if self.bank else ""))
        if not self.bank:
            box.add_widget(self.card_label("Load an Excel file first.", 16, True, TEXT, 70))
            box.add_widget(PrimaryButton(text="SELECT EXCEL", on_release=lambda *_: self.pick_excel()))
            return
        rows = [q for q in self.bank]
        attempts = correct = wrong = practiced = 0
        weak=[]; repeated=[]; mastered=[]
        section_data=defaultdict(lambda:[0,0])
        for q in rows:
            a,c,w,acc = self.stats(q)
            attempts += a; correct += c; wrong += w
            if a: practiced += 1
            if w and acc < 70: weak.append((acc,q))
            if w >= 3: repeated.append((w,q))
            if a >= 3 and acc >= 90: mastered.append(q)
            section_data[q["section"]][0] += c
            section_data[q["section"]][1] += a
        accuracy = correct/attempts*100 if attempts else 0
        box.add_widget(self.card_label(
            f"Questions practiced: {practiced}/{len(rows)}\nAttempts: {attempts}\nCorrect: {correct}   Wrong: {wrong}\nOverall accuracy: {accuracy:.1f}%",
            16, True, TEXT, 125))
        box.add_widget(self.card_label(
            f"WEAK: {len(weak)}   •   REPEATED WRONG: {len(repeated)}\nMASTERED: {len(mastered)}   •   BOOKMARKED: {len(self.bookmarks)}",
            15, True, ACCENT_DARK, 78))
        box.add_widget(SoftButton(text="WEAK QUESTIONS", on_release=lambda *_: self.quick_filter("Weak (<70%)")))
        box.add_widget(SoftButton(text="REPEATED WRONG", on_release=lambda *_: self.quick_filter("Repeated Wrong (3+)")))
        box.add_widget(SoftButton(text="WRONG QUESTIONS", on_release=lambda *_: self.quick_filter("Wrong Questions")))
        box.add_widget(SoftButton(text="BOOKMARKED", on_release=lambda *_: self.quick_filter("Bookmarked")))
        box.add_widget(SoftButton(text="MASTERED", on_release=lambda *_: self.quick_filter("Mastered")))
        box.add_widget(AdaptiveLabel(text="SECTION PERFORMANCE", bold=True, color=MUTED, size_hint_y=None, height=dp(30)))
        for sec,(c,a) in sorted(section_data.items()):
            pct = c/a*100 if a else 0
            box.add_widget(self.card_label(f"{sec}\n{pct:.0f}%  •  {a} attempts", 14, True, TEXT, 62))
        box.add_widget(SoftButton(text="BACK HOME", on_release=lambda *_: self.show_home()))

    def quick_filter(self,kind):
        # Build the targeted screen then start with 20.
        pool=[]
        for q in self.bank:
            a,c,w,acc=self.stats(q)
            ok = ((kind=="Wrong Questions" and w>0) or
                  (kind=="Repeated Wrong (3+)" and w>=3) or
                  (kind=="Weak (<70%)" and w>0 and acc<70) or
                  (kind=="Bookmarked" and q["id"] in self.bookmarks) or
                  (kind=="Mastered" and a>=3 and acc>=90))
            if ok: pool.append(q)
        if not pool:
            self.popup("No questions", f"No questions currently match: {kind}")
            return
        random.shuffle(pool)
        self.mode="practice"; self.quiz_questions=pool[:min(20,len(pool))]; self.begin_quiz()

    def show_bank_manager(self):
        box=self.content()
        box.add_widget(self.header("Question Bank"))
        box.add_widget(self.card_label(f"{self.current_file_name}\n{len(self.bank)} MCQs",17,True,ACCENT_DARK,75))
        box.add_widget(PrimaryButton(text="SELECT ANOTHER EXCEL", on_release=lambda *_: self.pick_excel()))
        box.add_widget(SoftButton(text="BACK", on_release=lambda *_: self.show_home()))

    def load_history(self):
        path = os.path.join(self.user_data_dir, "mcq_progress.json")
        self.history_path = path
        try:
            if os.path.exists(path):
                with open(path,"r",encoding="utf-8") as f:
                    data=json.load(f)
                    self.history=data if isinstance(data,dict) else {}
        except Exception:
            self.history={}

    def save_history(self):
        try:
            with open(self.history_path,"w",encoding="utf-8") as f:
                json.dump(self.history,f,ensure_ascii=False,indent=2)
        except Exception:
            pass

    def popup(self,title,message):
        content=BoxLayout(orientation="vertical",padding=dp(12),spacing=dp(10))
        content.add_widget(AdaptiveLabel(text=str(message),font_size=sp(15)))
        b=PrimaryButton(text="OK")
        content.add_widget(b)
        p=Popup(title=title,content=content,size_hint=(.88,.42))
        b.bind(on_release=p.dismiss); p.open()

if __name__ == "__main__":
    MCQApp().run()
