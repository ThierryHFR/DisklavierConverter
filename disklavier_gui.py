#!/usr/bin/env python3
"""Graphical interface for converting Yamaha Disklavier WAV files to MIDI."""
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from disklavier_converter import convert_file


def default_output_dir():
    """Return the conventional Windows Music/DisklaviertoMidi directory."""
    return Path.home() / 'Music' / 'DisklaviertoMidi'


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Disklavier Converter')
        self.geometry('720x460')
        self.minsize(620, 380)
        self.files = []
        self.messages = queue.Queue()
        self.running = False
        self.output_dir = tk.StringVar(value=str(default_output_dir()))
        self.status = tk.StringVar(value='Sélectionnez un ou plusieurs fichiers WAV Yamaha.')
        self._build_widgets()
        self.after(100, self._poll_messages)

    def _build_widgets(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text='Fichiers Disklavier Yamaha').grid(
            row=0, column=0, columnspan=2, sticky='w')
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(5, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=8)
        self.file_list.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.file_list.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.file_list.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 12))
        self.add_button = ttk.Button(buttons, text='Ajouter des fichiers…', command=self.add_files)
        self.add_button.pack(side='left')
        self.remove_button = ttk.Button(buttons, text='Retirer la sélection', command=self.remove_files)
        self.remove_button.pack(side='left', padx=(6, 0))
        self.clear_button = ttk.Button(buttons, text='Vider', command=self.clear_files)
        self.clear_button.pack(side='left', padx=(6, 0))

        ttk.Label(frame, text='Dossier de sortie').grid(row=3, column=0, sticky='w')
        output_frame = ttk.Frame(frame)
        output_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(5, 12))
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.output_dir).grid(row=0, column=0, sticky='ew')
        self.browse_button = ttk.Button(output_frame, text='Parcourir…', command=self.choose_output_dir)
        self.browse_button.grid(row=0, column=1, padx=(6, 0))

        self.progress = ttk.Progressbar(frame, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=2, sticky='ew')
        ttk.Label(frame, textvariable=self.status).grid(row=6, column=0, columnspan=2,
                                                        sticky='w', pady=(6, 8))
        self.convert_button = ttk.Button(frame, text='Convertir en MIDI', command=self.start_conversion)
        self.convert_button.grid(row=7, column=0, columnspan=2, sticky='e')

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title='Sélectionner les fichiers Disklavier',
            filetypes=[('Fichiers WAV', '*.wav *.WAV'), ('Tous les fichiers', '*.*')])
        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.file_list.insert(tk.END, path)
        self._update_status()

    def remove_files(self):
        selected = list(self.file_list.curselection())
        for index in reversed(selected):
            self.file_list.delete(index)
            del self.files[index]
        self._update_status()

    def clear_files(self):
        self.files.clear()
        self.file_list.delete(0, tk.END)
        self._update_status()

    def choose_output_dir(self):
        directory = filedialog.askdirectory(title='Choisir le dossier de sortie')
        if directory:
            self.output_dir.set(directory)

    def _update_status(self):
        self.status.set(f'{len(self.files)} fichier(s) sélectionné(s).')

    def _set_enabled(self, enabled):
        state = 'normal' if enabled else 'disabled'
        for widget in (self.add_button, self.remove_button, self.clear_button,
                       self.browse_button, self.convert_button):
            widget.configure(state=state)

    def start_conversion(self):
        if self.running:
            return
        if not self.files:
            messagebox.showwarning('Aucun fichier', 'Sélectionnez au moins un fichier WAV.')
            return
        output_dir = Path(self.output_dir.get()).expanduser()
        if not str(output_dir):
            messagebox.showwarning('Dossier manquant', 'Choisissez un dossier de sortie.')
            return
        self.running = True
        self._set_enabled(False)
        self.progress.configure(maximum=100, value=0)
        threading.Thread(target=self._convert_files, args=(list(self.files), output_dir),
                         daemon=True).start()

    def _convert_files(self, files, output_dir):
        results = []
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # Display the failing file without closing the GUI.
            for input_path in files:
                results.append((input_path, None, 0, exc))
            self.messages.put(('done', results))
            return
        total_files = len(files)
        for index, input_path in enumerate(files, 1):
            output_path = output_dir / (Path(input_path).stem + '.mid')
            try:
                def report_file_progress(value, file_index=index, file_name=Path(input_path).name):
                    overall = ((file_index - 1) + value) / total_files
                    self.messages.put(('progress', overall, file_index, total_files, file_name))

                count = convert_file(input_path, output_path,
                                     progress_callback=report_file_progress)
                results.append((input_path, output_path, count, None))
            except Exception as exc:  # Continue with the remaining selected files.
                results.append((input_path, None, 0, exc))
                self.messages.put(('progress', index / total_files, index, total_files,
                                   f'{Path(input_path).name} (erreur)'))
        self.messages.put(('done', results))

    def _poll_messages(self):
        try:
            while True:
                message = self.messages.get_nowait()
                if message[0] == 'progress':
                    _, overall, index, total, name = message
                    self.progress.configure(value=overall * 100)
                    self.status.set(f'{index}/{total} in progress: {name} ({overall:.0%})')
                else:
                    self._finish(message[1])
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)

    def _finish(self, results):
        self.running = False
        self._set_enabled(True)
        errors = [f'{Path(src).name} : {error}' for src, _, _, error in results if error]
        completed = len(results) - len(errors)
        if errors:
            self.status.set(f'{completed} fichier(s) converti(s), {len(errors)} erreur(s).')
            messagebox.showerror('Conversion terminée avec erreurs', '\n'.join(errors))
        else:
            self.status.set(f'{completed} fichier(s) converti(s).')
            messagebox.showinfo('Conversion terminée',
                                f'{completed} fichier(s) MIDI créé(s) dans :\n{self.output_dir.get()}')


if __name__ == '__main__':
    ConverterApp().mainloop()
