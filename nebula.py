import sqlite3
import re
from kivy.utils import platform
import os
import shutil
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.core.clipboard import Clipboard
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.label import MDLabel
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton

# 🔹 Konfigurasi Path Database
if platform == "android":
    from android.storage import app_storage_path
    app_path = app_storage_path()
    DB_PATH = os.path.join(app_path, "master.db")

    if not os.path.exists(DB_PATH):
        shutil.copyfile(os.path.join(os.getcwd(), "assets", "master.db"), DB_PATH)
else:
    DB_PATH = "master.db"

ITEMS_PER_PAGE = 10

KV = '''
ScreenManager:
    SearchScreen:

<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: 0.1, 0.1, 0.1, 1

        MDTopAppBar:
            title: "Cari Data Penduduk"
            elevation: 5
            pos_hint: {"top": 1}

        MDTextField:
            id: search_field
            hint_text: "Masukkan nama penduduk..."
            icon_right: "magnify"
            mode: "rectangle"
            pos_hint: {"center_x": 0.5}
            size_hint_x: 0.9
            on_text_validate: app.search_data()

        MDRaisedButton:
            text: "Cari"
            pos_hint: {"center_x": 0.5}
            on_release: app.search_data()

        MDLabel:
            id: info_label
            text: "Menampilkan 0 dari 0 data (Halaman 0/0)"
            halign: "center"
            font_size: "10sp"
            theme_text_color: "Hint"
            size_hint_y: None
            height: dp(20)
            pos_hint: {"center_x": 0.5, "y": 0}

        ScrollView:
            MDList:
                id: results_list

        MDBoxLayout:
            adaptive_height: True
            spacing: "10dp"
            pos_hint: {"center_x": 0.5}

            MDRaisedButton:
                text: "Previous"
                on_release: app.previous_page()
                disabled: True
                id: prev_button

            MDRaisedButton:
                text: "Next"
                on_release: app.next_page()
                disabled: True
                id: next_button

        MDLabel:
            text: "Created by apip0x1"
            halign: "center"
            theme_text_color: "Hint"
            font_size: "12sp"
            size_hint_y: None
            height: dp(20)
            padding_y: "10dp"
'''

class SearchScreen(Screen):
    pass

class StudentSearchApp(MDApp):
    dialog = None
    current_page = 0
    total_results = 0
    search_query = ""
    total_pages = 0
    data_cache = []

    def build(self):
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)

    def connect_db(self):
        return sqlite3.connect(DB_PATH)

    def search_data(self):
        search_text = self.root.get_screen("search").ids.search_field.text.lower()
        self.search_query = search_text
        self.current_page = 0
        self.fetch_data()

    def fetch_data(self):
        conn = self.connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM penduduk WHERE data LIKE ?", ('%' + self.search_query + '%',))
        self.total_results = cursor.fetchone()[0]
        self.total_pages = max(1, (self.total_results + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        offset = self.current_page * ITEMS_PER_PAGE
        cursor.execute(
            "SELECT data FROM penduduk WHERE data LIKE ? LIMIT ? OFFSET ?",
            ('%' + self.search_query + '%', ITEMS_PER_PAGE, offset)
        )
        self.data_cache = cursor.fetchall()
        conn.close()

        self.display_results()

    def display_results(self):
        results_list = self.root.get_screen("search").ids.results_list
        prev_button = self.root.get_screen("search").ids.prev_button
        next_button = self.root.get_screen("search").ids.next_button
        info_label = self.root.get_screen("search").ids.info_label

        results_list.clear_widgets()
        unique_data = []
        seen_numbers = set()

        for row in self.data_cache:
            text = row[0]
            if re.fullmatch(r"\d{16}", text):
                if text not in seen_numbers:
                    seen_numbers.add(text)
                    unique_data.append(text)
            else:
                unique_data.append(text)

        if unique_data:
            for row in unique_data:
                card = MDCard(
                    orientation="vertical",
                    size_hint_x=0.9,
                    size_hint_y=None,
                    height=dp(80),
                    pos_hint={"center_x": 0.5},
                    padding="10dp",
                    elevation=5,
                    radius=[15, 15, 15, 15]
                )

                label = MDLabel(
                    text=row,
                    theme_text_color="Primary",
                    halign="center",
                    size_hint_y=None,
                    height=dp(50),
                    shorten=True,
                    max_lines=2,
                    text_size=(None, None),
                )

                card.add_widget(label)
                card.bind(on_release=lambda x, t=row: self.show_detail_dialog(t))

                results_list.add_widget(card)
        else:
            self.show_dialog("Data tidak ditemukan")

        info_label.text = f"Menampilkan {len(unique_data)} dari {self.total_results} data (Halaman {self.current_page+1}/{self.total_pages})"

        prev_button.disabled = self.current_page == 0
        next_button.disabled = (self.current_page + 1) >= self.total_pages
    def next_page(self):
        if self.current_page + 1 < self.total_pages:
            self.current_page += 1
            self.fetch_data()

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.fetch_data()

    def show_detail_dialog(self, text):
        if self.dialog:
            self.dialog.dismiss()

        self.dialog = MDDialog(
            title="Detail Data",
            text=text,
            size_hint=(0.8, 0.4),
            buttons=[
                MDRaisedButton(text="Salin", on_release=lambda x: self.copy_to_clipboard(text)),
                MDRaisedButton(text="Tutup", on_release=lambda x: self.dialog.dismiss())
            ]
        )
        self.dialog.open()

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        snackbar = Snackbar(size_hint_x=0.8)
        snackbar.add_widget(MDLabel(text="Data berhasil disalin!", halign="center"))
        snackbar.open()

if __name__ == "__main__":
    StudentSearchApp().run()
