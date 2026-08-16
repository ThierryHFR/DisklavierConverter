#!/usr/bin/env python3
"""Graphical interface for converting Yamaha Disklavier WAV files to MIDI."""
import json
import locale
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from disklavier_converter import convert_file


def default_output_dir():
    """Return the conventional Windows Music/DisklaviertoMidi directory."""
    return Path.home() / 'Music' / 'DisklaviertoMidi'


LANGUAGE_NAMES = {'fr': 'Français', 'en': 'English', 'es': 'Español',
                  'it': 'Italiano', 'de': 'Deutsch'}


def resource_path(relative_path):
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return base / relative_path


def system_language():
    language = (locale.getlocale()[0] or locale.getdefaultlocale()[0] or 'en').lower()
    return language[:2] if language[:2] in LANGUAGE_NAMES else 'en'


def load_translations(language):
    try:
        with open(resource_path(f'locales/{language}.json'), encoding='utf-8') as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError):
        with open(resource_path('locales/en.json'), encoding='utf-8') as stream:
            return json.load(stream)


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Disklavier Converter')
        self.files = []
        self.messages = queue.Queue()
        self.running = False
        self.language = tk.StringVar(value=system_language())
        self.translations = {}
        self.output_dir = tk.StringVar(value=str(default_output_dir()))
        self.template_path = tk.StringVar()
        self.offset = tk.StringVar(value='1400')
        self.time_offset = tk.StringVar(value='-1.177')
        self.keep_setup = tk.BooleanVar(value=False)
        self.status = tk.StringVar()
        self._build_widgets()
        self._apply_language()
        self._fit_to_contents(initial=True)
        self.after(100, self._poll_messages)

    def tr(self, key, **values):
        text = self.translations.get(key, key)
        return text.format(**values)

    def _build_widgets(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        language_frame = ttk.Frame(frame)
        language_frame.grid(row=0, column=0, columnspan=2, sticky='e', pady=(0, 8))
        self.language_label = ttk.Label(language_frame)
        self.language_label.pack(side='left', padx=(0, 6))
        self.language_combo = ttk.Combobox(
            language_frame, textvariable=self.language, state='readonly', width=14,
            values=list(LANGUAGE_NAMES))
        self.language_combo.pack(side='left')
        self.language_combo.bind('<<ComboboxSelected>>', self.change_language)

        self.files_label = ttk.Label(frame)
        self.files_label.grid(row=1, column=0, columnspan=2, sticky='w')
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(5, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=8)
        self.file_list.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.file_list.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.file_list.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky='w', pady=(0, 12))
        self.add_button = ttk.Button(buttons, command=self.add_files)
        self.add_button.pack(side='left')
        self.remove_button = ttk.Button(buttons, command=self.remove_files)
        self.remove_button.pack(side='left', padx=(6, 0))
        self.clear_button = ttk.Button(buttons, command=self.clear_files)
        self.clear_button.pack(side='left', padx=(6, 0))

        self.output_label = ttk.Label(frame)
        self.output_label.grid(row=4, column=0, sticky='w')
        output_frame = ttk.Frame(frame)
        output_frame.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(5, 12))
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.output_dir).grid(row=0, column=0, sticky='ew')
        self.browse_button = ttk.Button(output_frame, command=self.choose_output_dir)
        self.browse_button.grid(row=0, column=1, padx=(6, 0))

        self.options_frame = ttk.LabelFrame(frame)
        self.options_frame.grid(row=6, column=0, columnspan=2, sticky='ew', pady=(0, 12))
        self.options_frame.columnconfigure(1, weight=1)
        self.template_label = ttk.Label(self.options_frame)
        self.template_label.grid(row=0, column=0, sticky='w', padx=(8, 6), pady=(8, 4))
        self.template_entry = ttk.Entry(self.options_frame, textvariable=self.template_path)
        self.template_entry.grid(
            row=0, column=1, sticky='ew', pady=(8, 4))
        self.template_browse_button = ttk.Button(
            self.options_frame, command=self.choose_template)
        self.template_browse_button.grid(row=0, column=2, padx=(6, 8), pady=(8, 4))
        self.offset_label = ttk.Label(self.options_frame)
        self.offset_label.grid(row=1, column=0, sticky='w', padx=(8, 6), pady=4)
        self.offset_entry = ttk.Entry(self.options_frame, textvariable=self.offset, width=12)
        self.offset_entry.grid(
            row=1, column=1, sticky='w', pady=4)
        self.time_offset_label = ttk.Label(self.options_frame)
        self.time_offset_label.grid(row=2, column=0, sticky='w', padx=(8, 6), pady=4)
        self.time_offset_entry = ttk.Entry(
            self.options_frame, textvariable=self.time_offset, width=12)
        self.time_offset_entry.grid(
            row=2, column=1, sticky='w', pady=4)
        self.keep_setup_check = ttk.Checkbutton(
            self.options_frame, variable=self.keep_setup)
        self.keep_setup_check.grid(row=3, column=0, columnspan=3, sticky='w', padx=8,
                                   pady=(4, 8))

        self.progress = ttk.Progressbar(frame, mode='determinate')
        self.progress.grid(row=7, column=0, columnspan=2, sticky='ew')
        self.status_label = ttk.Label(frame, textvariable=self.status)
        self.status_label.grid(row=8, column=0, columnspan=2, sticky='w', pady=(6, 8))
        self.convert_button = ttk.Button(frame, command=self.start_conversion)
        self.convert_button.grid(row=9, column=0, columnspan=2, sticky='e')

    def change_language(self, _event=None):
        self.translations = load_translations(self.language.get())
        self._apply_language()
        self._fit_to_contents()

    def _fit_to_contents(self, initial=False):
        """Keep the initial and minimum window size limited to its contents."""
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        self.minsize(width, height)
        if initial:
            self.geometry(f'{width}x{height}')

    def _apply_language(self):
        self.translations = self.translations or load_translations(self.language.get())
        self.title(self.tr('app_title'))
        self.language_label.configure(text=self.tr('language'))
        self.files_label.configure(text=self.tr('input_files'))
        self.add_button.configure(text=self.tr('add_files'))
        self.remove_button.configure(text=self.tr('remove_selected'))
        self.clear_button.configure(text=self.tr('clear'))
        self.output_label.configure(text=self.tr('output_folder'))
        self.browse_button.configure(text=self.tr('browse'))
        self.options_frame.configure(text=self.tr('advanced_options'))
        self.template_label.configure(text=self.tr('templates_file'))
        self.template_browse_button.configure(text=self.tr('browse'))
        self.offset_label.configure(text=self.tr('sample_offset'))
        self.time_offset_label.configure(text=self.tr('time_offset'))
        self.keep_setup_check.configure(text=self.tr('keep_setup'))
        self.convert_button.configure(text=self.tr('convert'))
        self._update_status()

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title=self.tr('select_files'),
            filetypes=[(self.tr('wav_files'), '*.wav *.WAV'),
                       (self.tr('all_files'), '*.*')])
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
        directory = filedialog.askdirectory(title=self.tr('choose_output'))
        if directory:
            self.output_dir.set(directory)

    def choose_template(self):
        path = filedialog.askopenfilename(
            title=self.tr('choose_templates'),
            filetypes=[(self.tr('template_files'), '*.bin'),
                       (self.tr('all_files'), '*.*')])
        if path:
            self.template_path.set(path)

    def _update_status(self):
        self.status.set(self.tr('selected_count', count=len(self.files)))

    def _set_enabled(self, enabled):
        state = 'normal' if enabled else 'disabled'
        for widget in (self.add_button, self.remove_button, self.clear_button,
                       self.browse_button, self.template_browse_button,
                       self.template_entry, self.offset_entry, self.time_offset_entry,
                       self.keep_setup_check, self.convert_button, self.language_combo):
            widget.configure(state=state)

    def start_conversion(self):
        if self.running:
            return
        if not self.files:
            messagebox.showwarning(self.tr('no_files_title'), self.tr('no_files_message'))
            return
        output_dir = Path(self.output_dir.get()).expanduser()
        if not str(output_dir):
            messagebox.showwarning(self.tr('missing_folder_title'),
                                   self.tr('missing_folder_message'))
            return
        try:
            offset = int(self.offset.get())
            time_offset = float(self.time_offset.get())
        except ValueError:
            messagebox.showwarning(self.tr('invalid_options_title'),
                                   self.tr('invalid_options_message'))
            return
        template_path = self.template_path.get().strip() or None
        self.running = True
        self._set_enabled(False)
        self.progress.configure(maximum=100, value=0)
        options = (template_path, offset, time_offset, self.keep_setup.get())
        threading.Thread(target=self._convert_files,
                         args=(list(self.files), output_dir, options), daemon=True).start()

    def _convert_files(self, files, output_dir, options):
        results = []
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # Display the failing file without closing the GUI.
            for input_path in files:
                results.append((input_path, None, 0, exc))
            self.messages.put(('done', results))
            return
        total_files = len(files)
        template_path, offset, time_offset, keep_setup = options
        for index, input_path in enumerate(files, 1):
            output_path = output_dir / (Path(input_path).stem + '.mid')
            try:
                def report_file_progress(value, file_index=index, file_name=Path(input_path).name):
                    overall = ((file_index - 1) + value) / total_files
                    self.messages.put(('progress', overall, file_index, total_files, file_name))

                count = convert_file(input_path, output_path,
                                     template_path=template_path, offset=offset,
                                     time_offset=time_offset, keep_setup=keep_setup,
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
                    self.status.set(self.tr('progress', index=index, total=total,
                                            name=name, percent=f'{overall:.0%}'))
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
            self.status.set(self.tr('finished_errors', completed=completed, errors=len(errors)))
            messagebox.showerror(self.tr('finished_errors_title'), '\n'.join(errors))
        else:
            self.status.set(self.tr('finished', completed=completed))
            messagebox.showinfo(self.tr('finished_title'),
                                self.tr('finished_message', completed=completed,
                                        output=self.output_dir.get()))


if __name__ == '__main__':
    ConverterApp().mainloop()
