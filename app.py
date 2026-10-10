import os
import sys
import json
import subprocess
import tkinter as tk
import customtkinter as ctk
import vlc
from tkinter import filedialog, messagebox
from CTkListbox import CTkListbox
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname


# =====================================================================
# CONFIGURATION DU CHEMIN VLC
# =====================================================================
vlc_path = r"C:\Program Files\VideoLAN\VLC"
if os.path.exists(vlc_path):
    os.add_dll_directory(vlc_path)
else:
    print(f"Attention : Le dossier VLC n'a pas été trouvé : {vlc_path}")


# =====================================================================
# FICHIER DE CONFIGURATION
# =====================================================================
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".media_player_config.json")


def _find_themes_folder():
    """Cherche le dossier des thèmes (local puis chemin absolu)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(script_dir, "themes")
    if os.path.isdir(local):
        return local
    hardcoded = r"D:\dossiers dans le bureau\thème pour customtkinter\CTkThemesPack\themes"
    if os.path.isdir(hardcoded):
        return hardcoded
    return None


THEMES_FOLDER = _find_themes_folder()

THEME_FILES = {
    "Bleu (défaut)": None,
    "Automne":       "autumn.json",
    "Brise":         "breeze.json",
    "Carotte":       "carrot.json",
    "Cerise":        "cherry.json",
    "Café":          "coffee.json",
    "Lavande":       "lavender.json",
    "Marais":        "marsh.json",
    "Métal":         "metal.json",
    "Minuit":        "midnight.json",
    "Orange":        "orange.json",
    "Patine":        "patina.json",
    "Rose vif":      "pink.json",
    "Rouge":         "red.json",
    "Givre":         "rime.json",
    "Rose":          "rose.json",
    "Ciel":          "sky.json",
    "Violet":        "violet.json",
    "Jaune":         "yellow.json",
}


def load_config():
    default = {"appearance_mode": "dark", "color_theme": "Bleu (défaut)"}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
        except Exception:
            return default
    return default


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur de sauvegarde config : {e}")


def apply_color_theme(theme_name):
    if theme_name == "Bleu (défaut)" or theme_name not in THEME_FILES:
        ctk.set_default_color_theme("blue")
        return
    filename = THEME_FILES[theme_name]
    if filename and THEMES_FOLDER:
        full_path = os.path.join(THEMES_FOLDER, filename)
        if os.path.exists(full_path):
            try:
                ctk.set_default_color_theme(full_path)
                print(f"[Thème] Appliqué : {theme_name} -> {full_path}")
                return
            except Exception as e:
                print(f"[Thème] Erreur pour {theme_name} : {e}")
    print(f"[Thème] Fichier introuvable pour {theme_name}, retour à 'blue'.")
    ctk.set_default_color_theme("blue")


CONFIG = load_config()
ctk.set_appearance_mode(CONFIG.get("appearance_mode", "dark"))
apply_color_theme(CONFIG.get("color_theme", "Bleu (défaut)"))

XSPF_NS = "http://xspf.org/ns/0/"
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
                    '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.vob'}


# =====================================================================
# PALETTE DE COULEURS ADAPTATIVES (clair, sombre)
# =====================================================================
# Format : (couleur_mode_clair, couleur_mode_sombre)
COLOR_SECTION_LABEL = ("gray30", "gray70")   # Libellés "─ FICHIERS ─"
COLOR_STATUS        = ("gray25", "gray80")   # Barre de statut
COLOR_VOLUME_LABEL  = ("gray25", "gray80")   # "🔊 Volume:"

# Couleurs des boutons (fg / hover)
COLOR_BTN_BLUE      = ("#2E6EA6", "#1E5A8A")
COLOR_BTN_BLUE_H    = ("#3D87C8", "#2E7BB8")
COLOR_BTN_RED       = ("#B22222", "#8B0000")
COLOR_BTN_RED_H     = ("#D13B3B", "#A52A2A")
COLOR_BTN_GRAY      = ("#909090", "#555555")
COLOR_BTN_GRAY_H    = ("#A8A8A8", "#777777")
COLOR_BTN_GREEN     = ("#3CB371", "#2E8B57")
COLOR_BTN_GREEN_H   = ("#52D18A", "#3CB371")
COLOR_BTN_ORANGE    = ("#DAA520", "#B8860B")
COLOR_BTN_ORANGE_H  = ("#F0BE3F", "#DAA520")
COLOR_BTN_INDIGO    = ("#6A0DAD", "#4B0082")
COLOR_BTN_INDIGO_H  = ("#8B2ECC", "#6A0DAD")


# =====================================================================
# CLASSE DE BASE : Logique commune audio/vidéo
# =====================================================================
class BasePlayerFrame(ctk.CTkFrame):
    def __init__(self, master, extensions, item_singular, item_plural):
        super().__init__(master, fg_color="transparent")

        self.extensions = extensions
        self.item_singular = item_singular
        self.item_plural = item_plural

        self.instance = vlc.Instance("--no-xlib", "--quiet", "--no-video-title-show")
        self.media_list = self.instance.media_list_new()
        self.player = self.instance.media_list_player_new()
        self.player.set_media_list(self.media_list)
        self.media_player = self.player.get_media_player()

        self.playlist_paths = []
        self.current_index = -1
        self.is_playing = False

        self.media_player.audio_set_volume(70)
        self._build_ui()

    def _build_ui(self):
        raise NotImplementedError

    def _get_filetypes(self):
        return [("Tous les fichiers", "*.*")]

    def _on_play_visual(self):
        pass

    def _on_stop_visual(self):
        pass

    def _build_right_panel(self, parent):
        panel = ctk.CTkFrame(parent, width=250)
        panel.grid_propagate(False)

        # ===== FICHIERS =====
        ctk.CTkLabel(
            panel, text="─ FICHIERS ─",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_SECTION_LABEL,
        ).pack(pady=(15, 5))

        ctk.CTkButton(panel, text=f"➕ Ajouter des {self.item_plural}",
                      command=self._add_files, height=38,
                      font=ctk.CTkFont(size=13)).pack(pady=3, padx=15, fill="x")

        ctk.CTkButton(panel, text="📂 Importer .xspf",
                      command=self._import_xspf, height=38,
                      fg_color=COLOR_BTN_BLUE, hover_color=COLOR_BTN_BLUE_H,
                      font=ctk.CTkFont(size=13)).pack(pady=3, padx=15, fill="x")

        ctk.CTkButton(panel, text="💾 Exporter .xspf",
                      command=self._export_xspf, height=38,
                      fg_color=COLOR_BTN_BLUE, hover_color=COLOR_BTN_BLUE_H,
                      font=ctk.CTkFont(size=13)).pack(pady=3, padx=15, fill="x")

        # ===== ÉDITION =====
        ctk.CTkLabel(
            panel, text="─ ÉDITION ─",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_SECTION_LABEL,
        ).pack(pady=(12, 5))

        ctk.CTkButton(panel, text="➖ Supprimer sélection",
                      command=self._remove_selected, height=35,
                      fg_color=COLOR_BTN_RED, hover_color=COLOR_BTN_RED_H,
                      font=ctk.CTkFont(size=12)).pack(pady=3, padx=15, fill="x")

        ctk.CTkButton(panel, text="🗑️ Vider la playlist",
                      command=self._clear_playlist, height=35,
                      fg_color=COLOR_BTN_GRAY, hover_color=COLOR_BTN_GRAY_H,
                      font=ctk.CTkFont(size=12)).pack(pady=3, padx=15, fill="x")

        # ===== LECTURE =====
        ctk.CTkLabel(
            panel, text="─ LECTURE ─",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_SECTION_LABEL,
        ).pack(pady=(12, 5))

        ctk.CTkButton(panel, text="▶️  Lecture",
                      command=self._play, height=40,
                      fg_color=COLOR_BTN_GREEN, hover_color=COLOR_BTN_GREEN_H,
                      font=ctk.CTkFont(size=14, weight="bold")).pack(pady=3, padx=15, fill="x")

        row = ctk.CTkFrame(panel, fg_color="transparent")
        row.pack(pady=3, padx=15, fill="x")

        ctk.CTkButton(row, text="⏸️ Pause", command=self._pause,
                      height=38,
                      fg_color=COLOR_BTN_ORANGE, hover_color=COLOR_BTN_ORANGE_H,
                      font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", fill="x", expand=True, padx=(0, 2))

        ctk.CTkButton(row, text="⏹️ Stop", command=self._stop,
                      height=38,
                      fg_color=COLOR_BTN_RED, hover_color=COLOR_BTN_RED_H,
                      font=ctk.CTkFont(size=12, weight="bold")).pack(side="right", fill="x", expand=True, padx=(2, 0))

        nav = ctk.CTkFrame(panel, fg_color="transparent")
        nav.pack(pady=3, padx=15, fill="x")

        ctk.CTkButton(nav, text="⏮️", command=self._prev_song,
                      height=35, font=ctk.CTkFont(size=16)).pack(side="left", fill="x", expand=True, padx=(0, 2))

        ctk.CTkButton(nav, text="⏭️", command=self._next_song,
                      height=35, font=ctk.CTkFont(size=16)).pack(side="right", fill="x", expand=True, padx=(2, 0))

        return panel

    def _build_status_and_volume(self, parent, row_status, row_volume):
        self.status_label = ctk.CTkLabel(
            parent, text=f"Aucun(e) {self.item_singular} chargé(e)",
            font=ctk.CTkFont(size=12), anchor="w",
            text_color=COLOR_STATUS,
        )
        self.status_label.grid(row=row_status, column=0, columnspan=2,
                               padx=10, pady=(5, 5), sticky="ew")

        vf = ctk.CTkFrame(parent, fg_color="transparent")
        vf.grid(row=row_volume, column=0, columnspan=2,
                padx=10, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(vf, text="🔊 Volume:",
                     font=ctk.CTkFont(size=12),
                     text_color=COLOR_VOLUME_LABEL).pack(side="left", padx=(0, 5))

        self.volume_slider = ctk.CTkSlider(vf, from_=0, to=100,
                                           command=self._set_volume, width=200)
        self.volume_slider.set(70)
        self.volume_slider.pack(side="left", padx=5)

        self.volume_value_label = ctk.CTkLabel(vf, text="70%",
                                               font=ctk.CTkFont(size=12),
                                               text_color=COLOR_VOLUME_LABEL)
        self.volume_value_label.pack(side="left", padx=5)

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title=f"Sélectionner des {self.item_plural}",
            filetypes=self._get_filetypes(),
        )
        if not files:
            return

        added = 0
        for f in files:
            if f in self.playlist_paths:
                continue
            self._add_single_file(f)
            added += 1

        self._update_status(
            f"{len(self.playlist_paths)} {self.item_plural} dans la playlist ({added} ajouté(s))"
        )

    def _add_single_file(self, filepath):
        media = self.instance.media_new(filepath)
        self.media_list.add_media(media)
        self.playlist_paths.append(filepath)
        self.playlist_box.insert("end", os.path.basename(filepath))

    def _remove_selected(self):
        selection = self.playlist_box.curselection()
        if selection is None:
            messagebox.showinfo("Info", f"Veuillez sélectionner un(e) {self.item_singular}.")
            return

        index = selection[0] if isinstance(selection, tuple) else selection
        self._remove_from_vlc(index)
        self.playlist_paths.pop(index)
        self.playlist_box.delete(index)

        if index == self.current_index:
            self.current_index = -1
            self.is_playing = False
        elif index < self.current_index:
            self.current_index -= 1

        self._update_status(f"{len(self.playlist_paths)} {self.item_plural} dans la playlist")

    def _remove_from_vlc(self, index):
        self.player.stop()
        new_media_list = self.instance.media_list_new()
        for i, path in enumerate(self.playlist_paths):
            if i != index:
                new_media_list.add_media(self.instance.media_new(path))
        self.media_list = new_media_list
        self.player.set_media_list(self.media_list)

    def _clear_playlist(self):
        if not self.playlist_paths:
            return
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment vider la playlist ?"):
            return

        self.player.stop()
        self.media_list = self.instance.media_list_new()
        self.player.set_media_list(self.media_list)
        self.playlist_paths.clear()
        self.playlist_box.delete(0, "end")
        self.current_index = -1
        self.is_playing = False
        self._on_stop_visual()
        self._update_status("Playlist vide")

    def _import_xspf(self):
        filepath = filedialog.askopenfilename(
            title="Importer une playlist XSPF",
            filetypes=[("Playlist XSPF", "*.xspf"), ("Tous les fichiers", "*.*")],
        )
        if not filepath:
            return

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            tracks = root.findall(f".//{{{XSPF_NS}}}track")
            if not tracks:
                tracks = root.findall(".//track")

            if not tracks:
                messagebox.showwarning("Playlist vide", "Aucune piste trouvée dans ce fichier XSPF.")
                return

            added = 0
            skipped = 0

            for track in tracks:
                loc_el = track.find(f"{{{XSPF_NS}}}location")
                if loc_el is None:
                    loc_el = track.find("location")
                if loc_el is None or not loc_el.text:
                    continue

                path = self._location_to_path(loc_el.text.strip())
                if not path or not os.path.exists(path):
                    skipped += 1
                    continue

                ext = os.path.splitext(path)[1].lower()
                if ext not in self.extensions:
                    skipped += 1
                    continue

                if path in self.playlist_paths:
                    continue

                self._add_single_file(path)
                added += 1

            msg = f"{added} piste(s) importée(s)."
            if skipped > 0:
                msg += f"\n{skipped} fichier(s) incompatible(s) ou introuvable(s) ignoré(s)."

            self._update_status(f"{len(self.playlist_paths)} {self.item_plural} dans la playlist")
            messagebox.showinfo("Import XSPF", msg)
        except Exception as e:
            messagebox.showerror("Erreur d'importation", f"Une erreur est survenue :\n{e}")

    def _export_xspf(self):
        if not self.playlist_paths:
            messagebox.showinfo("Info", "La playlist est vide, rien à exporter.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Exporter la playlist en XSPF",
            defaultextension=".xspf",
            filetypes=[("Playlist XSPF", "*.xspf")],
            initialfile="ma_playlist.xspf"
        )
        if not filepath:
            return

        try:
            playlist = ET.Element("playlist", {"version": "1", "xmlns": XSPF_NS})
            track_list = ET.SubElement(playlist, "trackList")

            for p in self.playlist_paths:
                track = ET.SubElement(track_list, "track")
                loc = ET.SubElement(track, "location")
                loc.text = self._path_to_location(p)
                title = ET.SubElement(track, "title")
                title.text = os.path.splitext(os.path.basename(p))[0]

            tree = ET.ElementTree(playlist)
            ET.indent(tree, space="  ")
            tree.write(filepath, encoding="UTF-8", xml_declaration=True)

            messagebox.showinfo("Export réussi", f"Playlist exportée dans :\n{filepath}")
            self._update_status(f"Playlist exportée : {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Erreur d'exportation", f"Impossible d'exporter :\n{e}")

    @staticmethod
    def _location_to_path(location):
        if location.startswith("file://"):
            try:
                parsed = urlparse(location)
                path = url2pathname(unquote(parsed.path))
                if os.name == "nt" and path.startswith("\\") and len(path) > 2 and path[2] == ":":
                    path = path[1:]
                return os.path.normpath(path)
            except Exception:
                return None
        else:
            return os.path.normpath(location) if os.path.exists(location) else None

    @staticmethod
    def _path_to_location(path):
        path = os.path.abspath(path).replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        return "file://" + path

    def _play(self):
        if not self.playlist_paths:
            messagebox.showinfo("Info", f"La playlist est vide. Ajoutez des {self.item_plural} d'abord.")
            return

        self._on_play_visual()

        if not self.is_playing:
            if self.current_index == -1:
                self.current_index = 0
                self.playlist_box.select(0)
            self.player.play_item_at_index(self.current_index)
            self.is_playing = True
            self._update_status(f"Lecture : {os.path.basename(self.playlist_paths[self.current_index])}")
        else:
            self.player.play()

    def _pause(self):
        if not self.is_playing:
            return
        self.player.pause()
        state = "Pause" if self.player.is_playing() == 0 else "Lecture"
        self._update_status(state)

    def _stop(self):
        self.player.stop()
        self.is_playing = False
        self._on_stop_visual()
        self._update_status("Arrêté")

    def _next_song(self):
        if not self.playlist_paths:
            return
        self._on_play_visual()
        self.player.next()
        self.current_index = (self.current_index + 1) % len(self.playlist_paths)
        self.playlist_box.select(self.current_index)
        self._update_status(f"Lecture : {os.path.basename(self.playlist_paths[self.current_index])}")

    def _prev_song(self):
        if not self.playlist_paths:
            return
        self._on_play_visual()
        self.player.previous()
        self.current_index = (self.current_index - 1) % len(self.playlist_paths)
        self.playlist_box.select(self.current_index)
        self._update_status(f"Lecture : {os.path.basename(self.playlist_paths[self.current_index])}")

    def _on_song_select(self, selected_value):
        if selected_value is None:
            return
        try:
            idx = self.playlist_box.get()
            if isinstance(idx, int):
                self.current_index = idx
        except Exception:
            for i in range(len(self.playlist_paths)):
                if self.playlist_box.get(i) == selected_value:
                    self.current_index = i
                    break

    def _set_volume(self, value):
        vol = int(float(value))
        self.media_player.audio_set_volume(vol)
        self.volume_value_label.configure(text=f"{vol}%")

    def _update_status(self, text):
        self.status_label.configure(text=text)

    def cleanup(self):
        try:
            self.player.stop()
            self.media_player.release()
            self.player.release()
            self.instance.release()
        except Exception:
            pass


# =====================================================================
# ONGLET AUDIO
# =====================================================================
class AudioPlayerFrame(BasePlayerFrame):
    def __init__(self, master):
        super().__init__(master, AUDIO_EXTENSIONS, "chanson", "chansons")

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.playlist_box = CTkListbox(
            self, width=450, height=400, command=self._on_song_select,
            font=ctk.CTkFont(size=13),
        )
        self.playlist_box.grid(row=0, column=0, padx=(5, 5), pady=5, sticky="nsew")

        right_panel = self._build_right_panel(self)
        right_panel.grid(row=0, column=1, padx=(5, 5), pady=5, sticky="ns")

        self._build_status_and_volume(self, row_status=1, row_volume=2)

    def _get_filetypes(self):
        return [
            ("Fichiers audio",
             "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma *.opus"),
            ("Tous les fichiers", "*.*"),
        ]


# =====================================================================
# ONGLET VIDÉO
# =====================================================================
class VideoPlayerFrame(BasePlayerFrame):
    def __init__(self, master):
        super().__init__(master, VIDEO_EXTENSIONS, "vidéo", "vidéos")
        self.after(500, self._attach_video_output)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=1)

        self.video_frame = tk.Frame(self, bg="black", highlightthickness=0)
        self.video_frame.grid(row=0, column=0, padx=(5, 5), pady=5, sticky="nsew")

        self.video_placeholder = tk.Label(
            self.video_frame,
            text="🎬 Aucune vidéo en cours\n\nAjoutez des fichiers ou importez une playlist .xspf",
            bg="black", fg="gray50",
            font=("Segoe UI", 13)
        )
        self.video_placeholder.pack(expand=True)

        self.playlist_box = CTkListbox(
            self, width=400, height=150, command=self._on_song_select,
            font=ctk.CTkFont(size=12),
        )
        self.playlist_box.grid(row=1, column=0, padx=(5, 5), pady=5, sticky="nsew")

        right_panel = self._build_right_panel(self)
        right_panel.grid(row=0, column=1, rowspan=2, padx=(5, 5), pady=5, sticky="ns")

        ctk.CTkButton(right_panel, text="🖥️ Plein écran",
                      command=self._toggle_fullscreen, height=35,
                      fg_color=COLOR_BTN_INDIGO, hover_color=COLOR_BTN_INDIGO_H,
                      font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(15, 3), padx=15, fill="x")

        self._build_status_and_volume(self, row_status=2, row_volume=3)

    def _get_filetypes(self):
        return [
            ("Fichiers vidéo",
             "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.mpg *.mpeg"),
            ("Tous les fichiers", "*.*"),
        ]

    def _attach_video_output(self, retry=0):
        try:
            self.video_frame.update_idletasks()
            hwnd = self.video_frame.winfo_id()
            if hwnd and hwnd > 0:
                if os.name == "nt":
                    self.media_player.set_hwnd(hwnd)
                else:
                    self.media_player.set_xwindow(hwnd)
                print(f"[Vidéo] Sortie attachée au HWND : {hwnd}")
            elif retry < 10:
                self.after(500, lambda: self._attach_video_output(retry + 1))
        except Exception as e:
            print(f"[Vidéo] Erreur d'attachement : {e}")
            if retry < 10:
                self.after(500, lambda: self._attach_video_output(retry + 1))

    def _on_play_visual(self):
        self.video_placeholder.pack_forget()

    def _on_stop_visual(self):
        try:
            self.video_placeholder.pack(expand=True)
        except Exception:
            pass

    def _toggle_fullscreen(self):
        top = self.winfo_toplevel()
        current = top.attributes("-fullscreen")
        top.attributes("-fullscreen", not current)


# =====================================================================
# FENÊTRE PRINCIPALE
# =====================================================================
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎵🎬 Lecteur multimédia")
        self.geometry("1250x820")
        self.minsize(1000, 680)

        # ==================================================================
        # BARRE SUPÉRIEURE
        # ==================================================================
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(top_bar, text="🎵🎬 Lecteur multimédia",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        self.theme_color_selector = ctk.CTkOptionMenu(
            top_bar,
            values=list(THEME_FILES.keys()),
            command=self._change_color_theme,
            font=ctk.CTkFont(size=12),
            width=150,
            height=32,
        )
        self.theme_color_selector.pack(side="right", padx=(10, 0))
        self.theme_color_selector.set(CONFIG.get("color_theme", "Bleu (défaut)"))

        self.theme_selector = ctk.CTkSegmentedButton(
            top_bar,
            values=["🌙 Sombre", "☀️ Clair", "💻 Système"],
            command=self._change_appearance_mode,
            font=ctk.CTkFont(size=12),
            height=32,
        )
        self.theme_selector.pack(side="right")

        mode_map = {"dark": "🌙 Sombre", "light": "☀️ Clair", "system": "💻 Système"}
        self.theme_selector.set(mode_map.get(CONFIG.get("appearance_mode", "dark"), "🌙 Sombre"))

        # ==================================================================
        # TABVIEW Audio / Vidéo
        # ==================================================================
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        self.tabview.add("🎵 Audio")
        self.tabview.add("🎬 Vidéo")

        self.audio_player = AudioPlayerFrame(self.tabview.tab("🎵 Audio"))
        self.audio_player.pack(fill="both", expand=True, padx=5, pady=5)

        self.video_player = VideoPlayerFrame(self.tabview.tab("🎬 Vidéo"))
        self.video_player.pack(fill="both", expand=True, padx=5, pady=5)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _change_appearance_mode(self, selected_value):
        mode_map = {"🌙 Sombre": "dark", "☀️ Clair": "light", "💻 Système": "system"}
        mode = mode_map.get(selected_value, "dark")
        ctk.set_appearance_mode(mode)

        CONFIG["appearance_mode"] = mode
        save_config(CONFIG)

    def _change_color_theme(self, selected_theme):
        CONFIG["color_theme"] = selected_theme
        save_config(CONFIG)

        if messagebox.askyesno(
            "Redémarrage nécessaire",
            f"Le thème « {selected_theme} » a été enregistré.\n\n"
            f"CustomTkinter ne permet pas de changer le thème de couleur "
            f"à chaud. Voulez-vous redémarrer l'application maintenant "
            f"pour l'appliquer ?"
        ):
            self._restart_app()

    def _restart_app(self):
        try:
            self.audio_player.cleanup()
            self.video_player.cleanup()
        except Exception:
            pass

        self.destroy()

        script_path = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script_path)
        extra_args = sys.argv[1:]

        subprocess.Popen(
            [sys.executable, script_path] + extra_args,
            cwd=script_dir,
        )
        sys.exit(0)

    def _on_close(self):
        self.audio_player.cleanup()
        self.video_player.cleanup()
        self.destroy()


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()