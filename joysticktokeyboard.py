import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkFont
import pygame
from pynput.keyboard import Controller as KeyboardController, Key as PyKeyboardKey
from pynput.mouse import Controller as MouseController, Button as PyMouseButton
import threading
import time
import json
import os

# pynput için özel klavye tuşları
PYNPUT_SPECIAL_KEYS = {
    'alt': PyKeyboardKey.alt, 'alt_l': PyKeyboardKey.alt_l, 'alt_r': PyKeyboardKey.alt_r,
    'alt_gr': PyKeyboardKey.alt_gr, 'backspace': PyKeyboardKey.backspace, 'caps_lock': PyKeyboardKey.caps_lock,
    'cmd': PyKeyboardKey.cmd, 'cmd_l': PyKeyboardKey.cmd_l, 'cmd_r': PyKeyboardKey.cmd_r,
    'ctrl': PyKeyboardKey.ctrl, 'ctrl_l': PyKeyboardKey.ctrl_l, 'ctrl_r': PyKeyboardKey.ctrl_r,
    'delete': PyKeyboardKey.delete, 'down': PyKeyboardKey.down, 'end': PyKeyboardKey.end,
    'enter': PyKeyboardKey.enter, 'esc': PyKeyboardKey.esc,
    'home': PyKeyboardKey.home, 'insert': PyKeyboardKey.insert, 'left': PyKeyboardKey.left,
    'media_next': PyKeyboardKey.media_next, 'media_play_pause': PyKeyboardKey.media_play_pause,
    'media_previous': PyKeyboardKey.media_previous, 'media_volume_down': PyKeyboardKey.media_volume_down,
    'media_volume_mute': PyKeyboardKey.media_volume_mute, 'media_volume_up': PyKeyboardKey.media_volume_up,
    'menu': PyKeyboardKey.menu, 'num_lock': PyKeyboardKey.num_lock, 'page_down': PyKeyboardKey.page_down,
    'page_up': PyKeyboardKey.page_up, 'pause': PyKeyboardKey.pause, 'print_screen': PyKeyboardKey.print_screen,
    'right': PyKeyboardKey.right, 'scroll_lock': PyKeyboardKey.scroll_lock,
    'shift': PyKeyboardKey.shift, 'shift_l': PyKeyboardKey.shift_l, 'shift_r': PyKeyboardKey.shift_r,
    'space': PyKeyboardKey.space, 'tab': PyKeyboardKey.tab, 'up': PyKeyboardKey.up,
    'win': PyKeyboardKey.cmd
}
for i in range(1, 21):
    PYNPUT_SPECIAL_KEYS[f'f{i}'] = getattr(PyKeyboardKey, f'f{i}')

# Fare Eylemleri için Özel Stringler
MOUSE_ACTIONS = {
    "mouse_left_click": PyMouseButton.left,
    "mouse_right_click": PyMouseButton.right,
    "mouse_middle_click": PyMouseButton.middle
}
# Fare hareketi ve kaydırma için eksen rolleri
MOUSE_AXIS_ROLES = ["mouse_x", "mouse_y", "mouse_scroll_x", "mouse_scroll_y"]

CONFIG_FILE_NAME = "advanced_gamepad_mappings.json"

class GamepadMapperApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Gelişmiş Oyun Kolu Eşleştirici (Klavye + Fare)")
        self.root.geometry("750x700")

        # pygame'i başlat
        pygame.init()
        pygame.joystick.init()

        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        self.joystick = None
        self.mapping_active = False
        self.mapping_thread = None

        # Basılı tutulan eylemleri takip etmek için
        self.pressed_actions = {}
        self.axis_scroll_states = {}

        self.default_settings = {
            "mappings": {
                "button_0": "mouse_left_click",
                "button_1": "mouse_right_click",
                "button_2": "space",
                "button_3": "e",
                "axis_0_neg": "a",
                "axis_0_pos": "d",
                "axis_1_neg": "w",
                "axis_1_pos": "s",
                "axis_2": "mouse_x",
                "axis_3": "mouse_y",
                "hat_0_up": "up",
                "hat_0_down": "down",
                "hat_0_left": "left",
                "hat_0_right": "right"
            },
            "mouse_settings": {
                "sensitivity": 15.0,
                "axis_deadzone": 0.15,
                "y_axis_invert_factor": -1,
                "scroll_sensitivity_factor": 1.0,
                "scroll_mode_discrete_threshold": 0.75
            },
            "gamepad_settings": {
                "keyboard_axis_threshold": 0.6
            }
        }
        self.settings = {}

        self.setup_ui()
        self.load_joysticks()
        self.load_settings_from_file()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _get_pynput_key(self, key_name_str):
        if not isinstance(key_name_str, str): 
            return key_name_str
        return PYNPUT_SPECIAL_KEYS.get(key_name_str.lower(), key_name_str)

    def setup_ui(self):
        # Ana çerçeve
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(expand=True, fill="both")

        # Sol Sütun
        left_column = ttk.Frame(main_frame)
        left_column.pack(side="left", fill="y", padx=(0, 10))

        # Joystick Seçimi
        controls_frame = ttk.LabelFrame(left_column, text="Oyun Kolu Kontrolleri")
        controls_frame.pack(padx=5, pady=5, fill="x")

        ttk.Label(controls_frame, text="Oyun Kolu:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.joystick_var = tk.StringVar()
        self.joystick_combo = ttk.Combobox(controls_frame, textvariable=self.joystick_var, state="readonly", width=30)
        self.joystick_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.joystick_combo.bind("<<ComboboxSelected>>", self.on_joystick_select)

        self.refresh_button = ttk.Button(controls_frame, text="Yenile", command=self.load_joysticks)
        self.refresh_button.grid(row=0, column=2, padx=5, pady=5)

        # Test butonu ekleyelim
        self.test_button = ttk.Button(controls_frame, text="Joystick Test Et", command=self.test_joystick)
        self.test_button.grid(row=1, column=0, padx=5, pady=5)

        self.start_button = ttk.Button(controls_frame, text="Eşleştirmeyi Başlat", command=self.start_mapping)
        self.start_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky="ew")
        self.stop_button = ttk.Button(controls_frame, text="Eşleştirmeyi Durdur", command=self.stop_mapping, state="disabled")
        self.stop_button.grid(row=2, column=2, padx=5, pady=10, sticky="ew")

        # Gamepad Ayarları
        self.gamepad_settings_frame = ttk.LabelFrame(left_column, text="Gamepad Ayarları")
        self.gamepad_settings_frame.pack(padx=5, pady=10, fill="x")
        self.kb_axis_thresh_var = tk.DoubleVar(value=self.default_settings["gamepad_settings"]["keyboard_axis_threshold"])
        
        ttk.Label(self.gamepad_settings_frame, text="Klavye Eksen Eşiği:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Scale(self.gamepad_settings_frame, from_=0.1, to=1.0, variable=self.kb_axis_thresh_var, orient="horizontal").grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(self.gamepad_settings_frame, textvariable=self.kb_axis_thresh_var).grid(row=0, column=2, padx=5, pady=2, sticky="w")

        # Fare Ayarları
        self.mouse_settings_frame = ttk.LabelFrame(left_column, text="Fare Ayarları")
        self.mouse_settings_frame.pack(padx=5, pady=10, fill="x")

        self.mouse_sensitivity_var = tk.DoubleVar(value=self.default_settings["mouse_settings"]["sensitivity"])
        self.mouse_deadzone_var = tk.DoubleVar(value=self.default_settings["mouse_settings"]["axis_deadzone"])
        self.mouse_y_invert_var = tk.IntVar(value=self.default_settings["mouse_settings"]["y_axis_invert_factor"])
        self.mouse_scroll_sens_var = tk.DoubleVar(value=self.default_settings["mouse_settings"]["scroll_sensitivity_factor"])
        self.mouse_scroll_thresh_var = tk.DoubleVar(value=self.default_settings["mouse_settings"]["scroll_mode_discrete_threshold"])

        ttk.Label(self.mouse_settings_frame, text="Hassasiyet:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Scale(self.mouse_settings_frame, from_=1.0, to=50.0, variable=self.mouse_sensitivity_var, orient="horizontal").grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(self.mouse_settings_frame, textvariable=self.mouse_sensitivity_var).grid(row=0, column=2, padx=5, pady=2, sticky="w")

        ttk.Label(self.mouse_settings_frame, text="Eksen Ölü Bölge:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Scale(self.mouse_settings_frame, from_=0.0, to=0.5, variable=self.mouse_deadzone_var, orient="horizontal").grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(self.mouse_settings_frame, textvariable=self.mouse_deadzone_var).grid(row=1, column=2, padx=5, pady=2, sticky="w")

        ttk.Label(self.mouse_settings_frame, text="Y Ekseni Ters Çevir:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        y_invert_frame = ttk.Frame(self.mouse_settings_frame)
        y_invert_frame.grid(row=2, column=1, columnspan=2, sticky="ew")
        ttk.Radiobutton(y_invert_frame, text="Evet (-1)", variable=self.mouse_y_invert_var, value=-1).pack(side="left", padx=2)
        ttk.Radiobutton(y_invert_frame, text="Hayır (1)", variable=self.mouse_y_invert_var, value=1).pack(side="left", padx=2)

        ttk.Label(self.mouse_settings_frame, text="Kaydırma Hassasiyeti:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        ttk.Scale(self.mouse_settings_frame, from_=0.1, to=5.0, variable=self.mouse_scroll_sens_var, orient="horizontal").grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(self.mouse_settings_frame, textvariable=self.mouse_scroll_sens_var).grid(row=3, column=2, padx=5, pady=2, sticky="w")

        ttk.Label(self.mouse_settings_frame, text="Kaydırma Eşiği (Eksen):").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        ttk.Scale(self.mouse_settings_frame, from_=0.1, to=1.0, variable=self.mouse_scroll_thresh_var, orient="horizontal").grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(self.mouse_settings_frame, textvariable=self.mouse_scroll_thresh_var).grid(row=4, column=2, padx=5, pady=2, sticky="w")

        # Sağ Sütun (JSON Editörü)
        right_column = ttk.Frame(main_frame)
        right_column.pack(side="left", expand=True, fill="both")

        # Tuş Atama Editörü
        mappings_frame = ttk.LabelFrame(right_column, text="JSON Ayar Editörü")
        mappings_frame.pack(padx=5, pady=5, fill="both", expand=True)

        self.settings_text = scrolledtext.ScrolledText(mappings_frame, wrap=tk.WORD, height=25, undo=True)
        default_font = tkFont.nametofont("TkTextFont")
        self.settings_text.configure(font=(default_font.actual("family"), default_font.actual("size")))
        self.settings_text.pack(padx=5, pady=5, fill="both", expand=True)

        self.save_button = ttk.Button(mappings_frame, text="JSON Ayarlarını Kaydet ve Uygula", command=self.save_settings_to_file)
        self.save_button.pack(pady=5)

        # Durum Çubuğu
        self.status_var = tk.StringVar()
        self.status_var.set("Hazır.")
        status_label = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0), padx=2)

    def test_joystick(self):
        """Joystick'in çalışıp çalışmadığını test eden fonksiyon"""
        if not self.joystick:
            messagebox.showwarning("Uyarı", "Önce bir joystick seçin!")
            return
        
        def test_loop():
            test_window = tk.Toplevel(self.root)
            test_window.title("Joystick Test")
            test_window.geometry("400x300")
            
            test_text = scrolledtext.ScrolledText(test_window, wrap=tk.WORD)
            test_text.pack(fill="both", expand=True, padx=10, pady=10)
            
            test_text.insert(tk.END, f"Joystick: {self.joystick.get_name()}\n")
            test_text.insert(tk.END, f"Tuş sayısı: {self.joystick.get_numbuttons()}\n")
            test_text.insert(tk.END, f"Eksen sayısı: {self.joystick.get_numaxes()}\n")
            test_text.insert(tk.END, f"Hat sayısı: {self.joystick.get_numhats()}\n\n")
            test_text.insert(tk.END, "Joystick'inizdeki tuşlara basın ve analog çubukları hareket ettirin...\n\n")
            
            def close_test():
                test_window.destroy()
            
            close_button = ttk.Button(test_window, text="Kapat", command=close_test)
            close_button.pack(pady=5)
            
            # Test döngüsü
            def update_test():
                if not test_window.winfo_exists():
                    return
                
                try:
                    pygame.event.pump()
                    
                    # Tuşları kontrol et
                    for i in range(self.joystick.get_numbuttons()):
                        if self.joystick.get_button(i):
                            test_text.insert(tk.END, f"Tuş {i} basıldı!\n")
                            test_text.see(tk.END)
                    
                    # Eksenleri kontrol et
                    for i in range(self.joystick.get_numaxes()):
                        axis_value = self.joystick.get_axis(i)
                        if abs(axis_value) > 0.1:  # Sadece belirgin hareketleri göster
                            test_text.insert(tk.END, f"Eksen {i}: {axis_value:.3f}\n")
                            test_text.see(tk.END)
                    
                    # Hat'ları kontrol et
                    for i in range(self.joystick.get_numhats()):
                        hat_value = self.joystick.get_hat(i)
                        if hat_value != (0, 0):
                            test_text.insert(tk.END, f"Hat {i}: {hat_value}\n")
                            test_text.see(tk.END)
                    
                    test_window.after(50, update_test)  # 50ms sonra tekrar kontrol et
                    
                except Exception as e:
                    test_text.insert(tk.END, f"Hata: {e}\n")
                    test_text.see(tk.END)
            
            update_test()
        
        threading.Thread(target=test_loop, daemon=True).start()

    def update_ui_from_settings(self):
        """Ayarlar yüklendikten sonra GUI elemanlarını günceller."""
        self.settings_text.delete(1.0, tk.END)
        self.settings_text.insert(tk.END, json.dumps(self.settings, indent=4))

        ms = self.settings.get("mouse_settings", self.default_settings["mouse_settings"])
        gs = self.settings.get("gamepad_settings", self.default_settings["gamepad_settings"])

        self.mouse_sensitivity_var.set(ms.get("sensitivity", self.default_settings["mouse_settings"]["sensitivity"]))
        self.mouse_deadzone_var.set(ms.get("axis_deadzone", self.default_settings["mouse_settings"]["axis_deadzone"]))
        self.mouse_y_invert_var.set(ms.get("y_axis_invert_factor", self.default_settings["mouse_settings"]["y_axis_invert_factor"]))
        self.mouse_scroll_sens_var.set(ms.get("scroll_sensitivity_factor", self.default_settings["mouse_settings"]["scroll_sensitivity_factor"]))
        self.mouse_scroll_thresh_var.set(ms.get("scroll_mode_discrete_threshold", self.default_settings["mouse_settings"]["scroll_mode_discrete_threshold"]))
        self.kb_axis_thresh_var.set(gs.get("keyboard_axis_threshold", self.default_settings["gamepad_settings"]["keyboard_axis_threshold"]))

    def load_settings_from_ui_and_text(self):
        """GUI elemanlarından ve JSON metninden ayarları self.settings'e yükler."""
        try:
            text_content = self.settings_text.get(1.0, tk.END)
            loaded_json_settings = json.loads(text_content)

            self.settings["mappings"] = loaded_json_settings.get("mappings", self.default_settings["mappings"])

            current_mouse_settings = {
                "sensitivity": self.mouse_sensitivity_var.get(),
                "axis_deadzone": self.mouse_deadzone_var.get(),
                "y_axis_invert_factor": self.mouse_y_invert_var.get(),
                "scroll_sensitivity_factor": self.mouse_scroll_sens_var.get(),
                "scroll_mode_discrete_threshold": self.mouse_scroll_thresh_var.get()
            }
            current_gamepad_settings = {
                "keyboard_axis_threshold": self.kb_axis_thresh_var.get()
            }
            self.settings["mouse_settings"] = current_mouse_settings
            self.settings["gamepad_settings"] = current_gamepad_settings

            self.status_var.set("Ayarlar GUI ve metin alanından başarıyla birleştirildi.")
            self.update_ui_from_settings()
            return True
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Hatası", f"Tuş atama metnindeki format geçersiz: {e}")
            self.status_var.set("Hata: JSON formatı geçersiz.")
            return False
        except Exception as e:
            messagebox.showerror("Hata", f"Ayarlar yüklenirken bir hata oluştu: {e}")
            self.status_var.set(f"Hata: Ayarlar yüklenemedi: {e}")
            return False

    def save_settings_to_file(self):
        if not self.load_settings_from_ui_and_text():
            return
        try:
            with open(CONFIG_FILE_NAME, "w") as f:
                json.dump(self.settings, f, indent=4)
            self.status_var.set(f"Ayarlar '{CONFIG_FILE_NAME}' dosyasına kaydedildi.")
        except Exception as e:
            messagebox.showerror("Kayıt Hatası", f"Ayarlar kaydedilemedi: {e}")
            self.status_var.set(f"Hata: Ayarlar kaydedilemedi: {e}")

    def load_settings_from_file(self):
        try:
            if os.path.exists(CONFIG_FILE_NAME):
                with open(CONFIG_FILE_NAME, "r") as f:
                    self.settings = json.load(f)
                self.status_var.set(f"Ayarlar '{CONFIG_FILE_NAME}' dosyasından yüklendi.")
            else:
                self.settings = json.loads(json.dumps(self.default_settings))
                self.status_var.set("Ayar dosyası bulunamadı. Varsayılan ayarlar kullanılıyor.")
        except Exception as e:
            self.settings = json.loads(json.dumps(self.default_settings))
            messagebox.showerror("Yükleme Hatası", f"Ayarlar yüklenemedi: {e}. Varsayılanlar kullanılıyor.")
            self.status_var.set(f"Hata: Ayarlar yüklenemedi. Varsayılanlar kullanılıyor.")
        self.update_ui_from_settings()

    def load_joysticks(self):
        """Joystick'leri yeniden tara ve listeye ekle"""
        try:
            # pygame joystick modülünü yeniden başlat
            pygame.joystick.quit()
            pygame.joystick.init()
            
            joystick_count = pygame.joystick.get_count()
            print(f"Bulunan joystick sayısı: {joystick_count}")  # Debug için
            
            joysticks_names = []
            for i in range(joystick_count):
                try:
                    js = pygame.joystick.Joystick(i)
                    name = js.get_name()
                    joysticks_names.append(f"{i}: {name}")
                    print(f"Joystick {i}: {name}")  # Debug için
                except pygame.error as e:
                    print(f"Joystick {i} okunamadı: {e}")
                    continue
            
            self.joystick_combo['values'] = joysticks_names
            
            if joysticks_names:
                self.joystick_combo.current(0)
                self.on_joystick_select(None)
                self.status_var.set(f"{joystick_count} oyun kolu bulundu.")
            else:
                self.joystick_var.set("")
                self.joystick = None
                self.status_var.set("Oyun kolu bulunamadı. USB kablosunu kontrol edin.")
                self.start_button.config(state="disabled")
                self.test_button.config(state="disabled")
                
        except Exception as e:
            print(f"Joystick yükleme hatası: {e}")
            self.status_var.set(f"Joystick yükleme hatası: {e}")

    def on_joystick_select(self, event):
        selected_name = self.joystick_var.get()
        if not selected_name:
            return

        try:
            # Seçilen joystick'in index'ini al (format: "0: Xbox Controller")
            joystick_index = int(selected_name.split(":")[0])
            
            # Eski joystick'i kapat
            if self.joystick:
                self.joystick.quit()
            
            # Yeni joystick'i başlat
            self.joystick = pygame.joystick.Joystick(joystick_index)
            self.joystick.init()
            
            num_axes = self.joystick.get_numaxes()
            num_buttons = self.joystick.get_numbuttons()
            num_hats = self.joystick.get_numhats()
            
            self.status_var.set(f"Seçildi: {self.joystick.get_name()} ({num_buttons} tuş, {num_axes} eksen, {num_hats} şapka)")
            self.start_button.config(state="normal")
            self.test_button.config(state="normal")
            return
            
        except (ValueError, IndexError, pygame.error) as e:
            print(f"Joystick seçme hatası: {e}")
            self.start_button.config(state="disabled")
            self.test_button.config(state="disabled")
            self.status_var.set(f"Joystick seçme hatası: {e}")

    def start_mapping(self):
        if not self.joystick:
            messagebox.showerror("Hata", "Lütfen önce bir oyun kolu seçin.")
            return
        if not self.load_settings_from_ui_and_text():
            return

        self.mapping_active = True
        self.toggle_ui_state(enable=False)
        self.mapping_thread = threading.Thread(target=self.mapping_loop_logic, daemon=True)
        self.mapping_thread.start()
        self.status_var.set(f"Eşleştirme aktif: {self.joystick.get_name()}")

    def stop_mapping(self):
        self.mapping_active = False
        if self.mapping_thread and self.mapping_thread.is_alive():
            self.mapping_thread.join(timeout=1)

        # Basılı kalan tüm eylemleri serbest bırak
        for gamepad_input, (action_type, pynput_obj) in list(self.pressed_actions.items()):
            try:
                if action_type == "keyboard":
                    self.keyboard.release(pynput_obj)
                elif action_type == "mouse_button":
                    self.mouse.release(pynput_obj)
            except Exception as e:
                print(f"Eylem serbest bırakma hatası ({pynput_obj}): {e}")
        self.pressed_actions.clear()
        self.axis_scroll_states.clear()

        self.toggle_ui_state(enable=True)
        self.status_var.set("Eşleştirme durduruldu.")

    def toggle_ui_state(self, enable):
        """GUI elemanlarının durumunu değiştirir."""
        state = "normal" if enable else "disabled"
        readonly_state = "readonly" if enable else "disabled"

        self.start_button.config(state="normal" if enable else "disabled")
        self.stop_button.config(state="disabled" if enable else "normal")
        self.test_button.config(state="normal" if enable else "disabled")

        self.joystick_combo.config(state=readonly_state)
        self.refresh_button.config(state=state)
        self.settings_text.config(state=state)
        self.save_button.config(state=state)

        for child in self.gamepad_settings_frame.winfo_children() + self.mouse_settings_frame.winfo_children():
            if isinstance(child, (ttk.Scale, ttk.Radiobutton, ttk.Entry)):
                child.config(state=state)

    def mapping_loop_logic(self):
        pygame.event.clear()
        gs = self.settings["gamepad_settings"]
        ms = self.settings["mouse_settings"]
        mappings = self.settings["mappings"]

        current_mouse_dx, current_mouse_dy = 0.0, 0.0
        current_scroll_dx, current_scroll_dy = 0, 0

        while self.mapping_active:
            try:
                pygame.event.pump()

                # TUŞLAR (Buttons)
                for i in range(self.joystick.get_numbuttons()):
                    button_id_str = f"button_{i}"
                    action_name = mappings.get(button_id_str)
                    if not action_name:
                        continue

                    is_pressed_now = self.joystick.get_button(i)

                    if action_name in MOUSE_ACTIONS:
                        mouse_button_obj = MOUSE_ACTIONS[action_name]
                        if is_pressed_now:
                            if button_id_str not in self.pressed_actions:
                                self.mouse.press(mouse_button_obj)
                                self.pressed_actions[button_id_str] = ("mouse_button", mouse_button_obj)
                        elif button_id_str in self.pressed_actions:
                            self.mouse.release(mouse_button_obj)
                            del self.pressed_actions[button_id_str]
                    else:  # Klavye tuşu
                        key_obj = self._get_pynput_key(action_name)
                        if is_pressed_now:
                            if button_id_str not in self.pressed_actions:
                                self.keyboard.press(key_obj)
                                self.pressed_actions[button_id_str] = ("keyboard", key_obj)
                        elif button_id_str in self.pressed_actions:
                            self.keyboard.release(key_obj)
                            del self.pressed_actions[button_id_str]

                # HATLAR (D-Pad)
                for i in range(self.joystick.get_numhats()):
                    hat_values = self.joystick.get_hat(i)
                    hat_map = {
                        (0, 1): "up", (0, -1): "down", (-1, 0): "left", (1, 0): "right",
                        (-1, 1): "upleft", (1, 1): "upright", (-1, -1): "downleft", (1, -1): "downright"
                    }
                    for val_tuple, direction_suffix in hat_map.items():
                        hat_id_str = f"hat_{i}_{direction_suffix}"
                        action_name = mappings.get(hat_id_str)
                        if not action_name:
                            continue

                        is_active_now = (hat_values == val_tuple)
                        key_obj = self._get_pynput_key(action_name)

                        if is_active_now:
                            if hat_id_str not in self.pressed_actions:
                                self.keyboard.press(key_obj)
                                self.pressed_actions[hat_id_str] = ("keyboard", key_obj)
                        elif hat_id_str in self.pressed_actions:
                            self.keyboard.release(key_obj)
                            del self.pressed_actions[hat_id_str]

                # EKSENLER (Analog Sticks)
                current_mouse_dx, current_mouse_dy = 0.0, 0.0
                current_scroll_dx, current_scroll_dy = 0, 0

                for i in range(self.joystick.get_numaxes()):
                    axis_value = self.joystick.get_axis(i)

                    # 1. Doğrudan eksen rolü ataması
                    axis_direct_role_id = f"axis_{i}"
                    direct_action_name = mappings.get(axis_direct_role_id)

                    if direct_action_name in MOUSE_AXIS_ROLES:
                        if abs(axis_value) > ms["axis_deadzone"]:
                            if direct_action_name == "mouse_x":
                                current_mouse_dx += axis_value * ms["sensitivity"]
                            elif direct_action_name == "mouse_y":
                                current_mouse_dy += axis_value * ms["sensitivity"] * ms["y_axis_invert_factor"]
                            elif direct_action_name == "mouse_scroll_y":
                                prev_scroll_state = self.axis_scroll_states.get(i, "neutral")
                                if axis_value > ms["scroll_mode_discrete_threshold"] and prev_scroll_state != "positive":
                                    current_scroll_dy += int(1 * ms["scroll_sensitivity_factor"])
                                    self.axis_scroll_states[i] = "positive"
                                elif axis_value < -ms["scroll_mode_discrete_threshold"] and prev_scroll_state != "negative":
                                    current_scroll_dy -= int(1 * ms["scroll_sensitivity_factor"])
                                    self.axis_scroll_states[i] = "negative"
                                elif -ms["scroll_mode_discrete_threshold"] < axis_value < ms["scroll_mode_discrete_threshold"]:
                                    self.axis_scroll_states[i] = "neutral"
                        else:
                            if direct_action_name in ["mouse_scroll_y", "mouse_scroll_x"]:
                                self.axis_scroll_states[i] = "neutral"

                    # 2. Eksen pozitif/negatif klavye ataması
                    elif direct_action_name is None:
                        axis_pos_id = f"axis_{i}_pos"
                        axis_neg_id = f"axis_{i}_neg"
                        action_pos = mappings.get(axis_pos_id)
                        action_neg = mappings.get(axis_neg_id)
                        kb_thresh = gs["keyboard_axis_threshold"]

                        if action_pos:
                            key_obj_pos = self._get_pynput_key(action_pos)
                            if axis_value > kb_thresh:
                                if axis_pos_id not in self.pressed_actions:
                                    self.keyboard.press(key_obj_pos)
                                    self.pressed_actions[axis_pos_id] = ("keyboard", key_obj_pos)
                            elif axis_pos_id in self.pressed_actions:
                                self.keyboard.release(key_obj_pos)
                                del self.pressed_actions[axis_pos_id]

                        if action_neg:
                            key_obj_neg = self._get_pynput_key(action_neg)
                            if axis_value < -kb_thresh:
                                if axis_neg_id not in self.pressed_actions:
                                    self.keyboard.press(key_obj_neg)
                                    self.pressed_actions[axis_neg_id] = ("keyboard", key_obj_neg)
                            elif axis_neg_id in self.pressed_actions:
                                self.keyboard.release(key_obj_neg)
                                del self.pressed_actions[axis_neg_id]

                # Fare hareketlerini uygula
                if current_mouse_dx != 0 or current_mouse_dy != 0:
                    self.mouse.move(current_mouse_dx, current_mouse_dy)

                # Fare kaydırmalarını uygula
                if current_scroll_dx != 0 or current_scroll_dy != 0:
                    self.mouse.scroll(current_scroll_dx, current_scroll_dy)

                time.sleep(0.005)  # ~200 Hz

            except pygame.error as e:
                print(f"Pygame hatası: {e}")
                self.root.after(0, self.stop_mapping_on_error, "Oyun kolu bağlantısı kesildi veya bir hata oluştu.")
                break
            except Exception as e:
                import traceback
                print(f"Eşleştirme döngüsünde beklenmedik hata: {e}\n{traceback.format_exc()}")
                self.root.after(0, self.stop_mapping_on_error, f"Beklenmedik bir hata oluştu: {e}")
                break

    def stop_mapping_on_error(self, error_message="Bilinmeyen bir hata oluştu."):
        if self.mapping_active:
            messagebox.showerror("Eşleştirme Hatası", f"{error_message}\nEşleştirme durduruluyor.")
            self.status_var.set(f"Hata: {error_message}. Eşleştirme durduruldu.")
            self.stop_mapping()

    def on_closing(self):
        if self.mapping_active:
            if messagebox.askokcancel("Çıkış", "Eşleştirme hala aktif. Çıkmak istediğinize emin misiniz?"):
                self.stop_mapping()
            else:
                return

        if self.joystick:
            self.joystick.quit()
        pygame.quit()
        self.root.destroy()

if __name__ == "__main__":
    try:
        pygame.init()
        main_root = tk.Tk()
        app = GamepadMapperApp(main_root)
        main_root.mainloop()
    except Exception as e:
        print(f"Program başlatma hatası: {e}")
        import traceback
        traceback.print_exc()
