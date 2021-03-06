#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of utext
#
# Copyright (C) 2012-2017 Lorenzo Carbonell
# lorenzo.carbonell.cerezo@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('GLib', '2.0')
    gi.require_version('WebKit', '3.0')
    gi.require_version('GtkSource', '3.0')
    gi.require_version('GtkSpell', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('Pango', '1.0')
except Exception as e:
    print(e, 'Repository version required not present')
    exit(1)
from gi.repository import GObject, Gtk, Gio, WebKit
from gi.repository import GLib
from gi.repository import Gdk, GtkSource, GtkSpell, GdkPixbuf
from gi.repository import Pango
import chardet
import os
import re
import datetime
import time
import codecs
import webbrowser
from markdown import Markdown
from jinja2 import Environment
from jinja2 import FileSystemLoader
from . import comun
from .comun import _
from .configurator import Configuration
from .driveapi import DriveService
from .services import DropboxService
from .insert_image_dialog import InsertImageDialog
from .insert_url_dialog import InsertUrlDialog
from .insert_table_dialog import InsertTableDialog
from .filename_dialog import FilenameDialog
from .files_in_cloud_dialog import FilesInCloudDialog
from .preferences_dialog import PreferencesDialog
from .table_editor import TableEditorDialog
from .search_dialog import SearchDialog
from .search_and_replace_dialog import SearchAndReplaceDialog
from .mdx_mathjax import MathExtension
from .myextension import MyExtension
from . import pypandoc
from . import pdfkit
from .keyboard_monitor import KeyboardMonitor

TIME_LAPSE = 0.3
COUNTER_TIME_LAPSE = 1
TAG_FOUND = 'found'
MATHJAX = '''
<script type="text/javascript"	src="https://cdn.mathjax.org/mathjax\
/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>
'''
EXPORT_FORMATS = [
    {'name': _('docx'),
     'typeof': 'docx',
     'extension': 'docx',
     'mimetype': 'application/vnd.openxmlformats-officedocument.\
wordprocessingml.document'},
    {'name': _('epub'),
     'typeof': 'epub3',
     'extension': 'epub',
     'mimetype': 'application/epub+zip'},
    {'name': _('html'),
     'typeof': 'html5',
     'extension': 'html',
     'mimetype': 'text/html'},
    {'name': _('latex'),
     'typeof': 'latex',
     'extension': 'latex',
     'mimetype': 'application/x-latex'},
    {'name': _('man'),
     'typeof': 'man',
     'extension': 'man',
     'mimetype': 'application/x-troff-man'},
    {'name': _('mediawiki'),
     'typeof': 'mediawiki',
     'extension': 'mediawiki',
     'mimetype': 'text/plain'},
    {'name': _('odt'),
     'typeof': 'odt',
     'extension': 'odt',
     'mimetype': 'application/vnd.oasis.opendocument.text'},
    {'name': _('pdf'),
     'typeof': 'pdf',
     'extension': 'pdf',
     'mimetype': 'application/pdf'},
    {'name': _('rtf'),
     'typeof': 'rtf',
     'extension': 'rtf',
     'mimetype': 'text/rtf'}]
env = Environment(loader=FileSystemLoader(comun.THEMESDIR))


def add2menu(menu, text=None, icon=None, conector_event=None,
             conector_action=None):
    if text is not None:
        menu_item = Gtk.ImageMenuItem.new_with_label(text)
        if icon:
            image = Gtk.Image.new_from_stock(icon, Gtk.IconSize.MENU)
            menu_item.set_image(image)
            menu_item.set_always_show_image(True)
    else:
        if icon is None:
            menu_item = Gtk.SeparatorMenuItem()
        else:
            menu_item = Gtk.ImageMenuItem.new_from_stock(icon, None)
            menu_item.set_always_show_image(True)
    if conector_event is not None and conector_action is not None:
        menu_item.connect(conector_event, conector_action)
    menu_item.show()
    menu.append(menu_item)
    return menu_item


class SimpleSeparator(Gtk.DrawingArea):
    def __init__(self):
        Gtk.Widget.__init__(self)
        self.set_size_request(8, 0)


class DoubleSeparator(Gtk.DrawingArea):
    def __init__(self):
        Gtk.Widget.__init__(self)
        self.set_size_request(16, 0)


class MainApplication(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(
            self,
            application_id='es.atareao.utext',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.license_type = Gtk.License.GPL_3_0
        print(3)

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def on_quit(self, widget, data):
        self.keyboardMonitor.stop()
        self.quit()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        print('do_startup')

        def create_action(name,
                          callback=self.action_clicked,
                          var_type=None,
                          value=None):
            if var_type is None:
                action = Gio.SimpleAction.new(name, None)
            else:
                action = Gio.SimpleAction.new_stateful(
                    name,
                    GLib.VariantType.new(var_type),
                    GLib.Variant(var_type, value)
                )
            action.connect('activate', callback)
            return action

        self.add_action(create_action("quit", callback=lambda *_: self.quit()))

        self.set_accels_for_action('app.add', ['<Ctrl>A'])
        self.set_accels_for_action('app.open', ['<Ctrl>O'])
        self.set_accels_for_action('app.quit', ['<Ctrl>Q'])
        self.set_accels_for_action('app.about', ['<Ctrl>F'])

        self.add_action(create_action(
            'new',
            callback=self.on_headbar_clicked))
        self.add_action(create_action(
            'open',
            callback=self.on_headbar_clicked))
        self.add_action(create_action(
            'close',
            callback=self.on_headbar_clicked))
        self.add_action(create_action(
            'save',
            callback=self.on_headbar_clicked))
        self.add_action(create_action(
            'save_as',
            callback=self.on_headbar_clicked))

        self.add_action(create_action(
            'set_preferences',
            callback=self.on_preferences_clicked))
        self.add_action(create_action(
            'goto_homepage',
            callback=lambda x, y: webbrowser.open(
                'http://www.atareao.es/apps/\
crear-un-gif-animado-de-un-video-en-ubuntu-en-un-solo-clic/')))
        self.add_action(create_action(
            'goto_bug',
            callback=lambda x, y: webbrowser.open(
                'https://bugs.launchpad.net/2gif')))
        self.add_action(create_action(
            'goto_sugestion',
            callback=lambda x, y: webbrowser.open(
                'https://blueprints.launchpad.net/2gif')))
        self.add_action(create_action(
            'goto_translation',
            callback=lambda x, y: webbrowser.open(
                'https://translations.launchpad.net/2gif')))
        self.add_action(create_action(
            'goto_questions',
            callback=lambda x, y: webbrowser.open(
                'https://answers.launchpad.net/2gif')))
        self.add_action(create_action(
            'goto_twitter',
            callback=lambda x, y: webbrowser.open(
                'https://twitter.com/atareao')))
        self.add_action(create_action(
            'goto_google_plus',
            callback=lambda x, y: webbrowser.open(
                'https://plus.google.com/\
118214486317320563625/posts')))
        self.add_action(create_action(
            'goto_facebook',
            callback=lambda x, y: webbrowser.open(
                'http://www.facebook.com/elatareao')))
        self.add_action(create_action(
            'goto_donate',
            callback=self.on_support_clicked))
        self.add_action(create_action(
            'about',
            callback=self.on_about_activate))

    def do_activate(self):
        print('activate')
        self.win = MainWindow(self)
        self.add_window(self.win)
        self.win.show()

    def action_clicked(self, action, variant):
        print(action, variant)
        if variant:
            action.set_state(variant)

    def on_support_clicked(self, widget, optional):
        dialog = SupportDialog(self.win)
        dialog.run()
        dialog.destroy()

    def on_headbar_clicked(self, action, optional):
        self.win.on_toolbar_clicked(action, action.get_name())

    def on_button_output_clicked(self, widget):
        dialog = Gtk.FileChooserDialog('Select output file',
                                       self.win, Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.REJECT,
                                        Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        dialog.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        dialog.set_filename(self.button_output.get_label())
        dialog.set_current_name(self.button_output.get_label().split('/')[-1])
        filter = Gtk.FileFilter()
        filter.set_name('Gif file')
        filter.add_mime_type("image/gif")
        dialog.add_filter(filter)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            dialog.hide()
            filename = dialog.get_filename()
            if not filename.endswith('.gif'):
                filename += '.gif'
            self.win.button_output.set_label(filename)
        dialog.destroy()

    def on_about_activate(self, widget, optional):
        ad = Gtk.AboutDialog()
        ad.set_name(comun.APPNAME)
        ad.set_version(comun.VERSION)
        ad.set_copyright('Copyrignt (c) 2011-2018\nLorenzo Carbonell')
        ad.set_comments(_('An application to write markdown'))
        ad.set_license('''
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
''')
        ad.set_website('http://www.atareao.es')
        ad.set_website_label('http://www.atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_documenters([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_translator_credits('\
Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>\n')
        ad.set_program_name('uText')
        ad.set_logo(GdkPixbuf.Pixbuf.new_from_file(comun.ICON))
        ad.run()
        ad.destroy()

    def on_preferences_clicked(self, widget, optional):
        cm = PreferencesDialog(self.win)
        if cm.run() == Gtk.ResponseType.ACCEPT:
            cm.close_ok()
        cm.destroy()


class MainWindow(Gtk.ApplicationWindow):
    __gsignals__ = {
        'text-changed': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                         (object,)),
        'save-me': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                    (object,)),
        'file-saved': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                       ()),
        'file-modified': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                          ()),
        'updated': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                    (str, str, int,)),
    }

    def __init__(self, app, afile=None):
        Gtk.ApplicationWindow.__init__(self, application=app)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_icon_from_file(comun.ICON)
        self.set_default_size(800, 600)
        self.connect('delete-event', self.on_close_application)
        self.connect('realize', self.on_activate_preview_or_html)
        self.connect('file-saved', self.on_file_saved)
        Gtk.IconTheme.get_default().append_search_path(comun.ICONDIR)
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        # Vertical box. Contains menu and PaneView
        self.vbox = Gtk.VBox(False, 0)
        self.add(self.vbox)

        self.app = app
        self.preferences = None
        self.current_filepath = None
        self.fileDriveId = None
        self.fileDropboxId = None
        self.fileDrive = None
        self.fileDropbox = None
        self.number_of_lines = 0
        self.contador = 0
        self.match_end = None
        self.searched_text = ''
        self.replacement_text = ''
        # self.timer = None
        self.glib_src = None

        self.launched = False
        self.is_saving = False

        css = open(os.path.join(comun.THEMESDIR, 'default', 'style.css'), 'r')
        self.css_content = css.read()
        css.close()
        # Actions
        insert_date = Gio.SimpleAction.new('insert-date', None)
        insert_date.connect('activate', self.on_toolbar_clicked)
        self.add_action(insert_date)
        insert_rule = Gio.SimpleAction.new('insert-horizontal-line', None)
        insert_rule.connect('activate', self.on_toolbar_clicked)
        self.add_action(insert_rule)
        insert_more = Gio.SimpleAction.new('insert-more', None)
        insert_more.connect('activate', self.on_toolbar_clicked)
        self.add_action(insert_more)
        insert_table = Gio.SimpleAction.new('insert-table', None)
        insert_table.connect('activate', self.on_toolbar_clicked)
        self.add_action(insert_table)
        create_table = Gio.SimpleAction.new('create-table', None)
        create_table.connect('activate', self.on_toolbar_clicked)
        self.add_action(create_table)
        # Init HeaderBar
        self.init_headerbar()

        # Init Menu
        self.init_menu()

        # Init Toolbar
        self.init_toolbar()

        # Markdown Editor
        self.writer = GtkSource.View.new()
        self.writer.set_left_margin(10)
        self.writer.set_right_margin(10)
        self.writer.set_top_margin(10)
        self.writer.set_bottom_margin(10)
        self.writer.set_name("markdownContent")
        self.writer.set_show_line_numbers(True)
        self.writer.set_show_line_marks(True)
        self.writer.set_insert_spaces_instead_of_tabs(True)
        self.writer.set_tab_width(4)
        self.writer.set_auto_indent(True)
        self.writer.set_wrap_mode(Gtk.WrapMode.WORD)
        self.writer.set_highlight_current_line(True)

        # Textbuffer
        buffer = GtkSource.Buffer()
        self.buffer_signal = buffer.connect("changed", self.on_buffer_changed)
        buffer.set_highlight_syntax(True)

        # Set textview buffer
        self.writer.set_buffer(buffer)
        # SpellChecker
        if GtkSpell._namespace == "Gtkspell":
            self.spellchecker = GtkSpell.Spell.new()
        elif GtkSpell._namespace == "GtkSpell":
            self.spellchecker = GtkSpell.Checker.new()
        self.spellchecker.attach(self.writer)
        lm = GtkSource.LanguageManager.get_default()
        language = lm.get_language("markdown")
        self.writer.get_buffer().set_language(language)

        # WebKit
        WebKit.set_cache_model(WebKit.CacheModel.DOCUMENT_VIEWER)
        self.webkit_viewer = WebKit.WebView()
        self.webkit_viewer.set_name("previewContent")
        self.webkit_viewer.connect(
            "navigation-policy-decision-requested", self.on_navigation)
        settings = WebKit.WebSettings()
        # settings.set_property('enable-file-access-from-file-uris', True)
        self.webkit_viewer.set_settings(settings)

        # Html
        self.html_viewer = GtkSource.View.new()
        self.html_viewer.set_left_margin(10)
        self.html_viewer.set_right_margin(10)
        self.html_viewer.set_top_margin(10)
        self.html_viewer.set_bottom_margin(10)
        self.html_viewer.set_name("htmlContent")
        self.html_viewer.set_show_line_numbers(True)
        self.html_viewer.set_show_line_marks(True)
        self.html_viewer.set_insert_spaces_instead_of_tabs(True)
        self.html_viewer.set_tab_width(4)
        self.html_viewer.set_auto_indent(True)
        self.html_viewer.set_wrap_mode(Gtk.WrapMode.WORD)

        bufferhtml = GtkSource.Buffer()
        bufferhtml.set_highlight_syntax(True)
        self.html_viewer.set_buffer(bufferhtml)
        lm = GtkSource.LanguageManager.get_default()
        language = lm.get_language("html")
        bufferhtml.set_language(language)

        # Scrolled Window 1 (for markdown)
        self.scrolledwindow1 = Gtk.ScrolledWindow()
        self.scrolledwindow1.set_hexpand(False)
        self.scrolledwindow1.set_vexpand(True)
        self.action_scroll1 = self.scrolledwindow1.get_vadjustment().connect(
            'value-changed', self.on_scrolled_value_changed, 'scroll1')

        # Scrolled Window 2 (for webkit)
        self.scrolledwindow2 = Gtk.ScrolledWindow()
        self.scrolledwindow2.set_hexpand(False)
        self.scrolledwindow2.set_vexpand(True)
        self.action_scroll2 = self.scrolledwindow2.get_vadjustment().connect(
            'value-changed', self.on_scrolled_value_changed_preview)

        # Scrolled Window 3 (for html)
        self.scrolledwindow3 = Gtk.ScrolledWindow()
        self.scrolledwindow3.set_hexpand(False)
        self.scrolledwindow3.set_vexpand(True)
        self.action_scroll3 = self.scrolledwindow3.get_vadjustment().connect(
            'value-changed', self.on_scrolled_value_changed_html)

        # Add textview, webkit and html
        self.scrolledwindow1.add(self.writer)
        self.scrolledwindow2.add(self.webkit_viewer)
        # self.webkit_viewer.set_view_source_mode(True)
        self.scrolledwindow3.add(self.html_viewer)

        # PaneView, contains markdown editor and html view (webkit)
        self.hpaned = Gtk.HPaned()
        self.hpaned.pack1(self.scrolledwindow1, True, True)

        self.stack = Gtk.Stack.new()
        self.stack.add_named(self.scrolledwindow2, 'viewer')
        self.stack.add_named(self.scrolledwindow3, 'html')
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)

        self.hpaned.pack2(self.stack, True, True)

        # Table Of Contents
        self.table_of_contents = WebKit.WebView()
        self.table_of_contents.set_name("tableofcontents")
        self.table_of_contents.connect(
            "navigation-policy-decision-requested", self.on_navigation2)
        settings = WebKit.WebSettings()
        # settings.set_property('enable-file-access-from-file-uris', True)
        self.table_of_contents.set_settings(settings)

        self.main_paned = Gtk.Paned()
        self.main_paned.pack1(self.table_of_contents, True, True)
        self.main_paned.pack2(self.hpaned, True, True)

        self.vbox.pack_start(self.main_paned, True, True, 0)

        # StatusBar
        self.statusbar = Gtk.Statusbar()
        self.vbox.pack_start(self.statusbar, False, False, 0)

        # Init Jinja, markdown
        self.init_template()

        # Load editor gtk styles
        self.load_styles()

        self.load_preferences()
        # Set windows title
        self.set_win_title()
        #
        self.resize(self.preferences['width'], self.preferences['height'])
        #
        self.show_all()
        self.show_source_code(False)
        if self.preferences['toolbar']:
            self.toolbar.set_visible(True)
            self.menus['toolbar'].set_label(_('Hide Toolbar'))
        else:
            self.toolbar.set_visible(False)
            self.menus['toolbar'].set_label(_('Show Toolbar'))
        if self.preferences['statusbar']:
            self.statusbar.set_visible(True)
            self.menus['statusbar'].set_label(_('Hide status bar'))
        else:
            self.statusbar.set_visible(False)
            self.menus['statusbar'].set_label(_('Show status bar'))
        self.apply_preferences()
        self.menus['undo'].set_sensitive(self.writer.get_buffer().can_undo)
        self.buttons['undo'].set_sensitive(self.writer.get_buffer().can_undo)
        self.menus['redo'].set_sensitive(self.writer.get_buffer().can_redo)
        self.buttons['redo'].set_sensitive(self.writer.get_buffer().can_redo)
        #
        self.number_of_lines = 0
        #
        self.match_end = None
        self.tag_found = self.writer.get_buffer().create_tag(
            TAG_FOUND, background="orange")

        self.writer.grab_focus()
        if afile is not None:
            self.load_file(afile)

        self.keyboardMonitor = KeyboardMonitor(800)
        self.keyboardMonitor.connect('key_released', self.do_it)
        self.keyboardMonitor.start()

    def on_file_saved(self, widget):
        if self.writer.get_buffer().get_modified() is True:
            print('---- saved ----')
            self.set_win_title(modified=False)
            self.writer.get_buffer().set_modified(False)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)

    def do_it(self, *args):
        if self.writer.get_buffer().get_modified() is True:
            if self.glib_src is not None:
                GLib.source_remove(self.glib_src)
                self.glib_src = None
            self.glib_src = GLib.idle_add(self.process_content)

    def process_content(self):
        print('aqui %d' % self.contador)
        html_content = None
        markdown_content = self.get_buffer_text()
        html_content = self.md.convert(markdown_content)
        print(self.md.toc)
        style = '''
        <style>
        ul, li{
            list-style-type: none;
        }
        div > ul > li > a{
            font-weight: bold;
        }
        a:link {
            color: black;
            text-decoration: none;
        }
        li{
            margin: 10px 0;
        }
        </style>
        '''

        self.table_of_contents.load_string(style + self.md.toc,
                                           'text/html',
                                           'utf-8',
                                           '')
        if self.html_viewer.is_visible():
            # html_content = self.md.convert(markdown_content)
            self.html_viewer.get_buffer().set_text(html_content)
        if self.webkit_viewer.is_visible():
            if self.preferences['mathjax']:
                mathjax = MATHJAX
            else:
                mathjax = ''
            if html_content is None:
                html_content = self.md.convert(markdown_content)
            html_rendered = self.jt.render(
                css=self.css_content, content=html_content, mathjax=mathjax)
            if html_rendered is not None:
                self.webkit_viewer.load_string(html_rendered,
                                               "text/html",
                                               "utf-8", '')




        self.statusbar.push(
            0, (_('Lines: {0}, Words: {1}, Characters: {2}')).format(
                len(re.findall('(\n)', markdown_content)),
                len(re.findall('(\S+)', markdown_content)),
                len(re.findall('(\w)', markdown_content))))
        self.contador += 1
        # self.timer = None
        self.glib_src = None
        self.set_win_title(modified=True)
        self.writer.get_buffer().set_modified(True)

    def apply_preferences(self):
        self.writer.set_show_line_numbers(
            self.preferences['markdown_editor.show_line_numbers'])
        self.writer.set_show_line_marks(
            self.preferences['markdown_editor.show_line_marks'])
        self.writer.set_insert_spaces_instead_of_tabs(
            self.preferences['markdown_editor.spaces'])
        self.writer.set_tab_width(
            self.preferences['markdown_editor.tab_width'])
        self.writer.set_auto_indent(
            self.preferences['markdown_editor.auto_indent'])
        self.writer.set_highlight_current_line(
            self.preferences['markdown_editor.highlight_current_line'])
        font = Pango.font_description_from_string(
            self.preferences['markdown_editor.font'])
        self.writer.modify_font(font)

        self.html_viewer.set_show_line_numbers(
            self.preferences['html_viewer.show_line_numbers'])
        self.html_viewer.set_show_line_marks(
            self.preferences['html_viewer.show_line_marks'])
        self.html_viewer.set_insert_spaces_instead_of_tabs(
            self.preferences['html_viewer.spaces'])
        self.html_viewer.set_tab_width(
            self.preferences['html_viewer.tab_width'])
        self.html_viewer.set_auto_indent(
            self.preferences['html_viewer.tab_width'])
        self.html_viewer.set_highlight_current_line(
            self.preferences['html_viewer.highlight_current_line'])
        css = open(
            os.path.join(
                comun.THEMESDIR,
                self.preferences['html_viewer.preview_theme'],
                'style.css'), 'r')
        self.css_content = css.read()
        css.close()

    def show_source_code(self, show):
        if show:
            self.stack.set_visible_child_name('html')
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        else:
            self.stack.set_visible_child_name('viewer')
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
        self.stack.get_visible_child().show_all()

    def load_preferences(self):
        configuration = Configuration()
        self.preferences = {}
        self.preferences['version'] = configuration.get('version')
        self.preferences['last_dir'] = configuration.get('last_dir')
        self.preferences['width'] = configuration.get('width')
        self.preferences['height'] = configuration.get('height')
        self.preferences['toolbar'] = configuration.get('toolbar')
        self.preferences['statusbar'] = configuration.get('statusbar')
        self.preferences['autosave'] = configuration.get('autosave')
        self.preferences['spellcheck'] = configuration.get('spellcheck')
        self.preferences['mathjax'] = configuration.get('mathjax')
        #
        self.preferences['markdown_editor.show_line_numbers'] =\
            configuration.get('markdown_editor.show_line_numbers')
        self.preferences['markdown_editor.show_line_marks'] =\
            configuration.get('markdown_editor.show_line_marks')
        self.preferences['markdown_editor.spaces'] =\
            configuration.get('markdown_editor.spaces')
        self.preferences['markdown_editor.tab_width'] =\
            configuration.get('markdown_editor.tab_width')
        self.preferences['markdown_editor.auto_indent'] =\
            configuration.get('markdown_editor.auto_indent')
        self.preferences['markdown_editor.highlight_current_line'] =\
            configuration.get('markdown_editor.highlight_current_line')
        self.preferences['markdown_editor.font'] =\
            configuration.get('markdown_editor.font')
        self.preferences['html_viewer.show_line_numbers'] =\
            configuration.get('html_viewer.show_line_numbers')
        self.preferences['html_viewer.show_line_marks'] =\
            configuration.get('html_viewer.show_line_marks')
        self.preferences['html_viewer.spaces'] =\
            configuration.get('html_viewer.spaces')
        self.preferences['html_viewer.tab_width'] =\
            configuration.get('html_viewer.tab_width')
        self.preferences['html_viewer.auto_indent'] =\
            configuration.get('html_viewer.auto_indent')
        self.preferences['html_viewer.highlight_current_line'] =\
            configuration.get('html_viewer.highlight_current_line')
        self.preferences['html_viewer.preview_theme'] =\
            configuration.get('html_viewer.preview_theme')
        self.preferences['dropbox'] = os.path.exists(comun.TOKEN_FILE)
        self.preferences['drive'] = os.path.exists(comun.TOKEN_FILE_DRIVE)
        #
        if len(self.preferences['last_dir']) == 0:
            self.preferences['last_dir'] = os.path.expanduser('~')
        self.preferences['last_filename'] = configuration.get('last_filename')
        self.preferences['filename1'] = configuration.get('filename1')
        self.preferences['filename2'] = configuration.get('filename2')
        self.preferences['filename3'] = configuration.get('filename3')
        self.preferences['filename4'] = configuration.get('filename4')
        #
        self.recents.set_sensitive(len(self.preferences['filename1']) > 0)
        self.filerecents['file1'].set_label(self.preferences['filename1'])
        self.filerecents['file1'].set_visible(
            len(self.preferences['filename1']) > 0)
        self.filerecents['file2'].set_label(self.preferences['filename2'])
        self.filerecents['file2'].set_visible(
            len(self.preferences['filename2']) > 0)
        self.filerecents['file3'].set_label(self.preferences['filename3'])
        self.filerecents['file3'].set_visible(
            len(self.preferences['filename3']) > 0)
        self.filerecents['file4'].set_label(self.preferences['filename4'])
        self.filerecents['file4'].set_visible(
            len(self.preferences['filename4']) > 0)
        if self.preferences['spellcheck']:
            self.spellchecker.attach(self.writer)
        else:
            self.spellchecker.detach()
        self.menus['save_on_dropbox'].set_sensitive(
            self.preferences['dropbox'])
        self.menus['save_on_drive'].set_sensitive(
            self.preferences['drive'])
        self.menus['open_from_dropbox'].set_sensitive(
            self.preferences['dropbox'])
        self.menus['open_from_drive'].set_sensitive(
            self.preferences['drive'])

    def save_preferences(self):
        configuration = Configuration()
        configuration.set('version', self.preferences['version'])
        configuration.set('last_dir', self.preferences['last_dir'])
        configuration.set('last_filename', self.preferences['last_filename'])
        configuration.set('filename1', self.preferences['filename1'])
        configuration.set('filename2', self.preferences['filename2'])
        configuration.set('filename3', self.preferences['filename3'])
        configuration.set('filename4', self.preferences['filename4'])
        arectangle = self.get_allocation()
        configuration.set('width', arectangle.width)
        configuration.set('height', arectangle.height)
        configuration.set('toolbar', self.toolbar.get_visible())
        configuration.set('statusbar', self.statusbar.get_visible())
        configuration.save()

    def on_scrolled_value_changed_preview(self, widget):
        value = self.scrolledwindow2.get_vadjustment().get_value()
        if value == 0:  # Fix
            self.on_scrolled_value_changed(None, 'scroll1')
        else:
            pass  # Something better?

    def on_scrolled_value_changed_html(self, widget):
        value = self.scrolledwindow3.get_vadjustment().get_value()
        if value == 0:  # Fix
            self.on_scrolled_value_changed(None, 'scroll1')
        else:
            pass  # Something better?

    def on_scrolled_value_changed(self, adjustment, scrolledwindow):
        self.scrolledwindow2.get_vadjustment().disconnect(self.action_scroll2)
        self.scrolledwindow3.get_vadjustment().disconnect(self.action_scroll3)
        page_size1 = self.scrolledwindow1.get_vadjustment().get_page_size()
        page_size2 = self.scrolledwindow2.get_vadjustment().get_page_size()
        page_size3 = self.scrolledwindow2.get_vadjustment().get_page_size()
        value1 = self.scrolledwindow1.get_vadjustment().get_value()
        value2 = self.scrolledwindow2.get_vadjustment().get_value()
        value3 = self.scrolledwindow3.get_vadjustment().get_value()
        lower1 = self.scrolledwindow1.get_vadjustment().get_lower()
        lower2 = self.scrolledwindow2.get_vadjustment().get_lower()
        lower3 = self.scrolledwindow3.get_vadjustment().get_lower()
        upper1 = self.scrolledwindow1.get_vadjustment().get_upper()
        upper2 = self.scrolledwindow2.get_vadjustment().get_upper()
        upper3 = self.scrolledwindow3.get_vadjustment().get_upper()
        pos1 = value1 + page_size1
        pos2 = value2 + page_size2
        pos3 = value3 + page_size2
        if pos1 == page_size1:
            pos2 = page_size2
            pos3 = page_size3
        elif pos1 == upper1:
            pos2 = upper2
            pos3 = upper3
        elif (upper1 - lower1) > 0:
            pos2 = pos1 * (upper2 - lower2) / (upper1 - lower1)
            pos3 = pos1 * (upper3 - lower3) / (upper1 - lower1)
        self.scrolledwindow2.get_vadjustment().set_value(pos2 - page_size2)
        self.scrolledwindow3.get_vadjustment().set_value(pos3 - page_size3)
        #
        self.action_scroll2 = self.scrolledwindow2.get_vadjustment().connect(
            'value-changed', self.on_scrolled_value_changed_preview)
        self.action_scroll3 = self.scrolledwindow3.get_vadjustment().connect(
            'value-changed', self.on_scrolled_value_changed_html)

    def load_file_dialog(self):
        dialog = Gtk.FileChooserDialog(
            "Open file", self,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_folder(self.preferences['last_dir'])
        self.add_filters(dialog)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            self.load_file(dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            pass  # TODO? User cancelled

        dialog.destroy()

    def on_menu_file_open(self, widget):
        filename = None
        if widget == self.filerecents['file1']:
            filename = self.preferences['filename1']
        elif widget == self.filerecents['file2']:
            filename = self.preferences['filename2']
        elif widget == self.filerecents['file3']:
            filename = self.preferences['filename3']
        elif widget == self.filerecents['file4']:
            filename = self.preferences['filename4']
        if filename is not None and os.path.exists(filename):
            self.load_file(filename)

    def work_with_file(self, filename):
        self.preferences['last_filename'] = filename
        self.preferences['last_dir'] = os.path.dirname(filename)
        if filename == self.preferences['filename1']:
            pass
        elif filename == self.preferences['filename2']:
            self.preferences['filename2'] = self.preferences['filename1']
            self.preferences['filename1'] = filename
        elif filename == self.preferences['filename3']:
            self.preferences['filename3'] = self.preferences['filename2']
            self.preferences['filename2'] = self.preferences['filename1']
            self.preferences['filename1'] = filename
        elif filename == self.preferences['filename4']:
            self.preferences['filename4'] = self.preferences['filename3']
            self.preferences['filename3'] = self.preferences['filename2']
            self.preferences['filename2'] = self.preferences['filename1']
            self.preferences['filename1'] = filename
        else:
            self.preferences['filename4'] = self.preferences['filename3']
            self.preferences['filename3'] = self.preferences['filename2']
            self.preferences['filename2'] = self.preferences['filename1']
            self.preferences['filename1'] = filename
        self.save_preferences()
        self.load_preferences()

    def load_file(self, file_path=None):
        self.current_filepath = file_path
        self.fileDriveId = None
        self.fileDropboxId = None
        self.fileDrive = None
        self.fileDropbox = None
        if self.current_filepath is not None:
            f = codecs.open(self.current_filepath, 'r', 'utf-8')
            data = f.read()
            f.close()
            self.writer.get_buffer().set_text(data)
            self.work_with_file(file_path)
            self.writer.grab_focus()
            self.do_it()
            self.save_current_file()

    def save_as(self):
        dialog = Gtk.FileChooserDialog(
            _('Select a file to save markdown'),
            self,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(self.preferences['last_dir'])
        filter = Gtk.FileFilter()
        filter.set_name(_('Markdown files'))
        filter.add_mime_type('text/plain')
        filter.add_pattern('*.md')
        dialog.add_filter(filter)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            if not filename.endswith('.md'):
                filename += '.md'
        else:
            dialog.destroy()
            return
        if os.path.exists(filename):
            dialog_overwrite = Gtk.MessageDialog(
                self, 0, Gtk.MessageType.WARNING,
                Gtk.ButtonsType.OK_CANCEL, _('File exists'))
            dialog_overwrite.format_secondary_text(_('Overwrite?'))
            response_overwrite = dialog_overwrite.run()
            if response_overwrite == Gtk.ResponseType.OK:
                dialog_overwrite.destroy()
                self.current_filepath = filename
                f = codecs.open(self.current_filepath,
                                'w',
                                'utf-8')
                f.write(self.get_buffer_text())
                f.close()
                self.emit('file-saved')
            else:
                dialog_overwrite.destroy()
        else:
            self.current_filepath = filename
            f = codecs.open(self.current_filepath,
                            'w',
                            'utf-8')
            f.write(self.get_buffer_text())
            f.close()
            self.emit('file-saved')

    def save_as_pdf(self):
        dialog = Gtk.FileChooserDialog(_('Select a file to save pdf'),
                                       self,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(self.preferences['last_dir'])
        filter = Gtk.FileFilter()
        filter.set_name(_('PDF files'))
        filter.add_mime_type('application/x-pdf')
        filter.add_pattern('*.pdf')
        dialog.add_filter(filter)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if filename is None:
                return
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            data = self.get_buffer_text()
            if data is not None:
                html_content = self.md.convert(data)
                encoding = chardet.detect(html_content)['encoding']
                options = {
                    'page-size': 'A4',
                    'margin-top': '20mm',
                    'margin-right': '15mm',
                    'margin-bottom': '20mm',
                    'margin-left': '25mm',
                    'encoding': encoding,
                }
                pdfkit.from_string(
                    html_content, filename, options=options)
        dialog.destroy()

    def save_current_file(self):
        if self.current_filepath is not None:
            f = codecs.open(self.current_filepath, 'w', 'utf-8')
            f.write(self.get_buffer_text())
            f.close()
            self.work_with_file(self.current_filepath)
            self.emit('file-saved')
        elif self.fileDropbox is not None:
            ds = DropboxService(comun.TOKEN_FILE)
            if os.path.exists(comun.TOKEN_FILE):
                ds.put_file(self.fileDropbox, self.get_buffer_text())
                self.emit('file-saved')
        elif self.fileDrive is not None:
            ds = DriveService(comun.TOKEN_FILE_DRIVE)
            if os.path.exists(comun.TOKEN_FILE_DRIVE):
                if self.fileDriveId is not None:
                    ans = ds.update_file(self.fileDriveId,
                                         self.fileDrive,
                                         self.get_buffer_text())
                else:
                    ans = ds.put_file(self.fileDrive, self.get_buffer_text())
                if ans is not None:
                    self.fileDriveId = ans['id']
                    self.emit('file-saved')
        else:
            self.save_as()

    def set_win_title(self, modified=False):
        if self.current_filepath and self.current_filepath is not None:
            current_path, current_filename = os.path.split(
                self.current_filepath)
            self.hb.set_subtitle(current_path)
        elif self.fileDropbox is not None:
            current_filename = self.fileDropbox
            self.hb.set_subtitle(_('Dropbox'))
        elif self.fileDrive is not None:
            current_filename = self.fileDrive
            self.hb.set_subtitle(_('Drive'))
        else:
            current_filename = _('Untitled')
            self.hb.set_subtitle('-')
        if modified is True:
            title = "uText * %s" % (current_filename)
        else:
            title = "uText - %s" % (current_filename)
        self.hb.set_title(title)

    def init_toolbar(self):
        self.toolbar = Gtk.Grid()
        self.toolbar.set_column_spacing(4)
        self.toolbar.set_margin_top(4)
        self.toolbar.set_margin_bottom(4)
        self.toolbar.set_margin_left(8)
        self.toolbar.set_margin_right(8)
        self.vbox.pack_start(self.toolbar, False, False, 0)
        #
        self.buttons = {}
        #
        menu_heading = Gio.Menu()
        menu_heading_01 = Gio.Menu()
        menu_heading.append_section(None, menu_heading_01)
        menu_heading_01.append_item(Gio.MenuItem.new(_('Heading 1'),
                                    'win.h01'))

        menu_heading_02 = Gio.Menu()
        menu_heading.append_section(None, menu_heading_02)
        menu_heading_02.append_item(Gio.MenuItem.new(_('Heading 2'),
                                    'win.h02'))

        menu_heading_03 = Gio.Menu()
        menu_heading.append_section(None, menu_heading_03)
        menu_heading_03.append_item(Gio.MenuItem.new(_('Heading 3'),
                                    'win.h03'))

        menu_heading_04 = Gio.Menu()
        menu_heading.append_section(None, menu_heading_04)
        menu_heading_04.append_item(Gio.MenuItem.new(_('Heading 4'),
                                    'win.h04'))

        menu_heading_05 = Gio.Menu()
        menu_heading.append_section(None, menu_heading_05)
        menu_heading_05.append_item(Gio.MenuItem.new(_('Heading 5'),
                                    'win.h05'))

        menu_heading_06 = Gio.Menu()
        menu_heading.append_section(None, menu_heading_06)
        menu_heading_06.append_item(Gio.MenuItem.new(_('Heading 6'),
                                    'win.h06'))

        self.buttons['mheading'] = Gtk.MenuButton()
        self.buttons['mheading'].add(Gtk.Label(_('Heading 1')))
        self.buttons['mheading'].set_menu_model(menu_heading)
        self.toolbar.add(self.buttons['mheading'])

        self.toolbar.add(SimpleSeparator())

        self.buttons['bold'] = Gtk.Button()
        self.buttons['bold'].add(Gtk.Image.new_from_icon_name(
            'utext-bold',
            Gtk.IconSize.BUTTON))
        self.buttons['bold'].connect(
            'clicked', self.on_toolbar_clicked, 'bold')
        self.toolbar.add(self.buttons['bold'])

        self.buttons['italic'] = Gtk.Button()
        self.buttons['italic'].add(Gtk.Image.new_from_icon_name(
            'utext-italic',
            Gtk.IconSize.BUTTON))
        self.buttons['italic'].connect(
            'clicked', self.on_toolbar_clicked, 'italic')
        self.toolbar.add(self.buttons['italic'])

        self.buttons['underline'] = Gtk.Button()
        self.buttons['underline'].add(Gtk.Image.new_from_icon_name(
            'utext-underline',
            Gtk.IconSize.BUTTON))
        self.buttons['underline'].connect(
            'clicked', self.on_toolbar_clicked, 'underline')
        self.toolbar.add(self.buttons['underline'])

        self.buttons['strikethrough'] = Gtk.Button()
        self.buttons['strikethrough'].add(Gtk.Image.new_from_icon_name(
            'utext-strikethrough',
            Gtk.IconSize.BUTTON))
        self.buttons['strikethrough'].connect(
            'clicked', self.on_toolbar_clicked, 'strikethrough')
        self.toolbar.add(self.buttons['strikethrough'])

        self.buttons['subscript'] = Gtk.Button()
        self.buttons['subscript'].add(Gtk.Image.new_from_icon_name(
            'utext-subscript',
            Gtk.IconSize.BUTTON))
        self.buttons['subscript'].connect(
            'clicked', self.on_toolbar_clicked, 'subscript')
        self.toolbar.add(self.buttons['subscript'])

        self.buttons['superscript'] = Gtk.Button()
        self.buttons['superscript'].add(Gtk.Image.new_from_icon_name(
            'utext-superscript',
            Gtk.IconSize.BUTTON))
        self.buttons['superscript'].connect(
            'clicked', self.on_toolbar_clicked, 'superscript')
        self.toolbar.add(self.buttons['superscript'])

        self.toolbar.add(SimpleSeparator())

        self.buttons['undo'] = Gtk.Button()
        self.buttons['undo'].add(Gtk.Image.new_from_icon_name(
            'utext-undo',
            Gtk.IconSize.BUTTON))
        self.buttons['undo'].connect(
            'clicked', self.on_toolbar_clicked, 'undo')
        self.toolbar.add(self.buttons['undo'])

        self.buttons['redo'] = Gtk.Button()
        self.buttons['redo'].add(Gtk.Image.new_from_icon_name(
            'utext-redo',
            Gtk.IconSize.BUTTON))
        self.buttons['redo'].connect(
            'clicked', self.on_toolbar_clicked, 'redo')
        self.toolbar.add(self.buttons['redo'])

        self.toolbar.add(SimpleSeparator())

        self.buttons['bullet-list'] = Gtk.Button()
        self.buttons['bullet-list'].add(Gtk.Image.new_from_icon_name(
            'utext-bullet-list',
            Gtk.IconSize.BUTTON))
        self.buttons['bullet-list'].connect(
            'clicked', self.on_toolbar_clicked, 'bullet-list')
        self.toolbar.add(self.buttons['bullet-list'])

        self.buttons['numbered-list'] = Gtk.Button()
        self.buttons['numbered-list'].add(Gtk.Image.new_from_icon_name(
            'utext-numbered-list',
            Gtk.IconSize.BUTTON))
        self.buttons['numbered-list'].connect(
            'clicked', self.on_toolbar_clicked, 'numbered-list')
        self.toolbar.add(self.buttons['numbered-list'])

        self.buttons['blockquote'] = Gtk.Button()
        self.buttons['blockquote'].add(Gtk.Image.new_from_icon_name(
            'utext-blockquote',
            Gtk.IconSize.BUTTON))
        self.buttons['blockquote'].connect(
            'clicked', self.on_toolbar_clicked, 'blockquote')
        self.toolbar.add(self.buttons['blockquote'])

        self.buttons['code'] = Gtk.Button()
        self.buttons['code'].add(Gtk.Image.new_from_icon_name(
            'utext-code',
            Gtk.IconSize.BUTTON))
        self.buttons['code'].connect(
            'clicked', self.on_toolbar_clicked, 'code')
        self.toolbar.add(self.buttons['code'])

        self.toolbar.add(SimpleSeparator())

        self.buttons['insert-link'] = Gtk.Button()
        self.buttons['insert-link'].add(Gtk.Image.new_from_icon_name(
            'utext-insert-link',
            Gtk.IconSize.BUTTON))
        self.buttons['insert-link'].connect(
            'clicked', self.on_toolbar_clicked, 'insert-link')
        self.toolbar.add(self.buttons['insert-link'])

        self.buttons['insert-image'] = Gtk.Button()
        self.buttons['insert-image'].add(Gtk.Image.new_from_icon_name(
            'utext-insert-image',
            Gtk.IconSize.BUTTON))
        self.buttons['insert-image'].connect(
            'clicked', self.on_toolbar_clicked, 'insert-image')
        self.toolbar.add(self.buttons['insert-image'])

        menu_insert = Gio.Menu()
        menu_insert.append_item(Gio.MenuItem.new(_('Insert date'),
                                                 'win.insert-date'))
        menu_insert.append_item(Gio.MenuItem.new(_('Insert horizontal line'),
                                                 'win.insert-horizontal-line'))
        menu_insert.append_item(Gio.MenuItem.new(_('Insert <!--more-->'),
                                                 'win.insert-more'))

        self.buttons['insert'] = Gtk.MenuButton()
        self.buttons['insert'].set_menu_model(menu_insert)
        self.buttons['insert'].add(Gtk.Image.new_from_icon_name(
            'utext-insert',
            Gtk.IconSize.BUTTON))
        self.toolbar.add(self.buttons['insert'])

        self.toolbar.add(SimpleSeparator())

        menu_table = Gio.Menu()
        menu_table.append(_('Insert table'), 'win.insert-table')
        menu_table.append(_('Insert table with editor'), 'win.create-table')

        menu_table_row = Gio.Menu()

        menu_table_row_add = Gio.Menu()
        menu_table_row_add.append(_('Add row before'), 'win.add-row-before')
        menu_table_row_add.append(_('Add row after'), 'win.add-row-after')

        menu_table_row.append_section(None, menu_table_row_add)
        menu_table_row.append(_('Remove row'), 'win.remove-row')
        menu_table.append_submenu(_('Rows'), menu_table_row)

        menu_table_column = Gio.Menu()

        menu_table_column_add = Gio.Menu()
        menu_table_column_add.append(_('Add column before'),
                                     'win.add-column-before')
        menu_table_column_add.append(_('Add column after'),
                                     'win.add-column-after')

        menu_table_column.append_section(None, menu_table_column_add)
        menu_table_column.append(_('Remove column'), 'win.remove-column')
        menu_table.append_submenu(_('Columns'), menu_table_column)

        self.buttons['table'] = Gtk.MenuButton()
        self.buttons['table'].set_menu_model(menu_table)
        self.buttons['table'].add(Gtk.Image.new_from_icon_name(
            'utext-table',
            Gtk.IconSize.BUTTON))
        self.toolbar.add(self.buttons['table'])

        '''
        self.buttons['new'] = Gtk.ToolButton(stock_id=Gtk.STOCK_NEW)
        self.buttons['new'].set_tooltip_text(_('New file'))
        self.buttons['new'].connect('clicked', self.on_toolbar_clicked, 'new')
        self.toolbar.add(self.buttons['new'])
        #
        self.buttons['open'] = Gtk.ToolButton(stock_id=Gtk.STOCK_OPEN)
        self.buttons['open'].set_tooltip_text(_('Open'))
        self.buttons['open'].connect(
            'clicked', self.on_toolbar_clicked, 'open')
        self.toolbar.add(self.buttons['open'])
        #
        self.buttons['close'] = Gtk.ToolButton(stock_id=Gtk.STOCK_CLOSE)
        self.buttons['close'].set_tooltip_text(_('Close'))
        self.buttons['close'].connect(
            'clicked', self.on_toolbar_clicked, 'close')
        self.toolbar.add(self.buttons['close'])
        #
        self.buttons['save'] = Gtk.ToolButton(stock_id=Gtk.STOCK_SAVE)
        self.buttons['save'].set_tooltip_text(_('Save'))
        self.buttons['save'].connect(
            'clicked', self.on_toolbar_clicked, 'save')
        self.toolbar.add(self.buttons['save'])
        #
        self.buttons['save_as'] = Gtk.ToolButton(stock_id=Gtk.STOCK_SAVE_AS)
        self.buttons['save_as'].set_tooltip_text(_('Save as'))
        self.buttons['save_as'].connect(
            'clicked', self.on_toolbar_clicked, 'save_as')
        self.toolbar.add(self.buttons['save_as'])
        #
        self.toolbar.add(Gtk.SeparatorToolItem())
        #
        self.buttons['undo'] = Gtk.ToolButton(stock_id=Gtk.STOCK_UNDO)
        self.buttons['undo'].set_tooltip_text(_('Undo'))
        self.buttons['undo'].connect(
            'clicked', self.on_toolbar_clicked, 'undo')
        self.toolbar.add(self.buttons['undo'])
        #
        self.buttons['redo'] = Gtk.ToolButton(stock_id=Gtk.STOCK_REDO)
        self.buttons['redo'].set_tooltip_text(_('Redo'))
        self.buttons['redo'].connect(
            'clicked', self.on_toolbar_clicked, 'redo')
        self.toolbar.add(self.buttons['redo'])
        #
        self.toolbar.add(Gtk.SeparatorToolItem())
        #
        self.buttons['bold'] = Gtk.ToolButton(stock_id=Gtk.STOCK_BOLD)
        self.buttons['bold'].set_tooltip_text(_('Bold'))
        self.buttons['bold'].connect(
            'clicked', self.on_toolbar_clicked, 'bold')
        self.toolbar.add(self.buttons['bold'])
        #
        self.buttons['italic'] = Gtk.ToolButton(stock_id=Gtk.STOCK_ITALIC)
        self.buttons['italic'].set_tooltip_text(_('Italic'))
        self.buttons['italic'].connect(
            'clicked', self.on_toolbar_clicked, 'italic')
        self.toolbar.add(self.buttons['italic'])
        #
        self.buttons['underline'] = Gtk.ToolButton(
            stock_id=Gtk.STOCK_UNDERLINE)
        self.buttons['underline'].set_tooltip_text(_('Underline'))
        self.buttons['underline'].connect(
            'clicked', self.on_toolbar_clicked, 'underline')
        self.toolbar.add(self.buttons['underline'])
        #
        self.buttons['strikethrough'] = Gtk.ToolButton(
            stock_id=Gtk.STOCK_STRIKETHROUGH)
        self.buttons['strikethrough'].set_tooltip_text(_('Strikethrough'))
        self.buttons['strikethrough'].connect(
            'clicked', self.on_toolbar_clicked, 'strikethrough')
        self.toolbar.add(self.buttons['strikethrough'])
        #
        self.toolbar.add(Gtk.SeparatorToolItem())
        #
        self.buttons['copy'] = Gtk.ToolButton(stock_id=Gtk.STOCK_COPY)
        self.buttons['copy'].set_tooltip_text(_('Copy'))
        self.buttons['copy'].connect(
            'clicked', self.on_toolbar_clicked, 'copy')
        self.toolbar.add(self.buttons['copy'])
        #
        self.buttons['paste'] = Gtk.ToolButton(stock_id=Gtk.STOCK_PASTE)
        self.buttons['paste'].set_tooltip_text(_('Paste'))
        self.buttons['paste'].connect(
            'clicked', self.on_toolbar_clicked, 'paste')
        self.toolbar.add(self.buttons['paste'])
        #
        self.buttons['cut'] = Gtk.ToolButton(stock_id=Gtk.STOCK_CUT)
        self.buttons['cut'].set_tooltip_text(_('Cut'))
        self.buttons['cut'].connect(
            'clicked', self.on_toolbar_clicked, 'cut')
        self.toolbar.add(self.buttons['cut'])
        #
        self.toolbar.add(Gtk.SeparatorToolItem())
        #
        self.buttons['zoom_in'] = Gtk.ToolButton(stock_id=Gtk.STOCK_ZOOM_IN)
        self.buttons['zoom_in'].set_tooltip_text(_('Zoom in'))
        self.buttons['zoom_in'].connect(
            'clicked', self.on_toolbar_clicked, 'zoom_in')
        self.toolbar.add(self.buttons['zoom_in'])
        #
        self.buttons['zoom_out'] = Gtk.ToolButton(stock_id=Gtk.STOCK_ZOOM_OUT)
        self.buttons['zoom_out'].set_tooltip_text(_('Zoom out'))
        self.buttons['zoom_out'].connect(
            'clicked', self.on_toolbar_clicked, 'zoom_out')
        self.toolbar.add(self.buttons['zoom_out'])
        #
        self.buttons['zoom_100'] = Gtk.ToolButton(stock_id=Gtk.STOCK_ZOOM_100)
        self.buttons['zoom_100'].set_tooltip_text(_('Zoom 100%'))
        self.buttons['zoom_100'].connect(
            'clicked', self.on_toolbar_clicked, 'zoom_100')
        self.toolbar.add(self.buttons['zoom_100'])
        '''

    def init_headerbar(self):
        self.menu = {}
        #
        self.hb = Gtk.HeaderBar()
        self.hb.set_show_close_button(True)
        self.hb.props.title = comun.APPNAME
        self.set_titlebar(self.hb)

        self.menu['file.menu'] = Gio.Menu()
        self.menu['file.menu.01'] = Gio.Menu()
        self.menu['file.menu'].append_section(None, self.menu['file.menu.01'])
        self.menu['file.menu.01.new_file'] = Gio.MenuItem.new(
            _('New file'), 'app.new')
        self.menu['file.menu.01.new_file'].set_icon(
            Gio.ThemedIcon.new_with_default_fallbacks(
                'insert-object-symbolic'))
        self.menu['file.menu.01'].append_item(
            self.menu['file.menu.01.new_file'])
        self.menu['file.menu.02'] = Gio.Menu()
        self.menu['file.menu'].append_section(None, self.menu['file.menu.02'])
        self.menu['file.menu.02.open'] = Gio.MenuItem.new(
            _('Open'), 'app.open')
        self.menu['file.menu.02.close'] = Gio.MenuItem.new(
            _('Close'), 'app.close')
        self.menu['file.menu.02'].append_item(
            self.menu['file.menu.02.open'])
        self.menu['file.menu.02'].append_item(
            self.menu['file.menu.02.close'])
        self.menu['file.menu.03'] = Gio.Menu()
        self.menu['file.menu'].append_section(None, self.menu['file.menu.03'])
        self.menu['file.menu.03.save'] = Gio.MenuItem.new(
            _('Open'), 'app.save')
        self.menu['file.menu.03.save_as'] = Gio.MenuItem.new(
            _('Close'), 'app.save_as')
        self.menu['file.menu.03'].append_item(
            self.menu['file.menu.03.save'])
        self.menu['file.menu.03'].append_item(
            self.menu['file.menu.03.save_as'])

        self.menu['file'] = Gtk.MenuButton()
        self.menu['file'].add(Gtk.Label(_('Open')))
        self.menu['file'].set_menu_model(self.menu['file.menu'])
        self.hb.pack_start(self.menu['file'])

        tools_popover = Gtk.Popover()
        tools_grid = Gtk.Grid()
        tools_grid.set_column_spacing(8)
        tools_grid.set_margin_top(8)
        tools_grid.set_margin_bottom(8)
        tools_grid.set_margin_left(8)
        tools_grid.set_margin_right(8)

        tools_popover.add(tools_grid)
        self.menu['print'] = Gtk.Button()
        self.menu['print'].set_tooltip_text(_('Print'))
        self.menu['print'].add(
            Gtk.Image.new_from_gicon(Gio.ThemedIcon(
                name='utext-print'), Gtk.IconSize.BUTTON))
        tools_grid.attach(self.menu['print'], 0, 0, 1, 1)
        self.menu['pdf'] = Gtk.Button()
        self.menu['pdf'].set_tooltip_text(_('Export to pdf'))
        self.menu['pdf'].add(
            Gtk.Image.new_from_gicon(Gio.ThemedIcon(
                name='utext-pdf'), Gtk.IconSize.BUTTON))
        tools_grid.attach(self.menu['pdf'], 1, 0, 1, 1)
        self.menu['full'] = Gtk.Button()
        self.menu['full'].set_tooltip_text(_('Enter full screen'))
        self.menu['full'].add(
            Gtk.Image.new_from_gicon(Gio.ThemedIcon(
                name='utext-full'), Gtk.IconSize.BUTTON))
        tools_grid.attach(self.menu['full'], 2, 0, 1, 1)
        tools_grid.attach(Gtk.Separator(), 0, 1, 3, 1)
        self.menu['tools.save-as'] = Gtk.MenuButton(_('Save as...'))
        tools_grid.attach(self.menu['tools.save-as'], 0, 2, 3, 1)

        self.menu['tools.menu'] = Gio.Menu()

        self.menu['tools.menu.01'] = Gio.Menu()
        section01 = Gio.MenuItem.new_section(None, self.menu['tools.menu.01'])
        section01.set_attribute_value('display-hint', GLib.Variant.new_string('horizontal-buttons'))
        self.menu['tools.menu'].append_item(section01)
        self.menu['tools.menu.01.new_file'] = Gio.MenuItem.new(None, 'app.new')
        self.menu['tools.menu.01.new_file'].set_attribute_value('label', GLib.Variant.new_string('Print'))
        self.menu['tools.menu.01.new_file'].set_attribute_value('verb-icon', GLib.Variant.new_string('utext-print'))
        self.menu['tools.menu.01'].append_item(self.menu['tools.menu.01.new_file'])
        self.menu['tools.menu.01.new_file1'] = Gio.MenuItem.new(None, 'app.new')
        self.menu['tools.menu.01.new_file1'].set_attribute_value('label', GLib.Variant.new_string('Print'))
        self.menu['tools.menu.01.new_file1'].set_attribute_value('verb-icon', GLib.Variant.new_string('utext-print'))
        self.menu['tools.menu.01'].append_item(self.menu['tools.menu.01.new_file1'])
        self.menu['tools.menu.01.new_file2'] = Gio.MenuItem.new(None, 'app.new')
        self.menu['tools.menu.01.new_file2'].set_attribute_value('label', GLib.Variant.new_string('Print'))
        self.menu['tools.menu.01.new_file2'].set_attribute_value('verb-icon', GLib.Variant.new_string('utext-print'))
        self.menu['tools.menu.01'].append_item(self.menu['tools.menu.01.new_file2'])

        self.menu['tools.menu.02'] = Gio.Menu()
        self.menu['tools.menu.02.new_file'] = Gio.MenuItem.new(None, 'app.new')
        self.menu['tools.menu.02.new_file'].set_attribute_value('label', GLib.Variant.new_string('Save as'))
        self.menu['tools.menu.02'].append_item(self.menu['tools.menu.02.new_file'])
        self.menu['tools.menu.02.new_file2'] = Gio.MenuItem.new(None, 'app.new')
        self.menu['tools.menu.02.new_file2'].set_attribute_value('label', GLib.Variant.new_string('Save as'))
        self.menu['tools.menu.02'].append_item(self.menu['tools.menu.02.new_file2'])
        self.menu['tools.menu.02.new_file3'] = Gio.MenuItem.new(None, 'app.new')
        self.menu['tools.menu.02.new_file3'].set_attribute_value('label', GLib.Variant.new_string('Save as'))
        self.menu['tools.menu.02'].append_item(self.menu['tools.menu.02.new_file3'])


        section02 = Gio.MenuItem.new_section(None, self.menu['tools.menu.02'])
        self.menu['tools.menu'].append_item(section02)

        max_action = Gio.SimpleAction.new_stateful("maximize", None,
                                                   GLib.Variant.new_boolean(False))
        #max_action.connect("change-state", self.on_maximize_toggle)
        self.add_action(max_action)

        menu_tools = Gio.Menu()
        menu_tools2 = Gio.MenuItem.new(None, 'win.maximize')
        menu_tools2.set_attribute_value('label', GLib.Variant.new_string('Check spelling'))
        menu_tools.append_item(menu_tools2)
        menu_tools3 = Gio.MenuItem.new(None, 'win.maximize')
        menu_tools3.set_attribute_value('label', GLib.Variant.new_string('Status bar'))
        menu_tools.append_item(menu_tools3)
        menu_tools4 = Gio.MenuItem.new(None, 'win.maximize')
        menu_tools4.set_attribute_value('label', GLib.Variant.new_string('Toolbar'))
        menu_tools.append_item(menu_tools4)

        self.menu['tools.menu'].append_submenu(_('Tools'), menu_tools)

        self.menu['tools.tools'] = Gtk.MenuButton()
        self.menu['tools.tools'].add(Gtk.Label(_('Tools')))
        #self.menu['tools.tools'].set_menu_model(self.menu['tools.menu'])
        #tools_grid.attach(self.menu['tools.tools'], 0, 3, 3, 1)

        tools_grid.show_all()

        self.menu['tools'] = Gtk.MenuButton()
        self.menu['tools'].set_menu_model(self.menu['tools.menu'])

        # self.menu['tools'].set_popover(tools_popover)
        # self.menu['tools'].connect('clicked', self.on_button_clicked)
        self.menu['tools'].add(Gtk.Image.new_from_gicon(
            Gio.ThemedIcon.new_with_default_fallbacks(
                'utext-tools'),
            Gtk.IconSize.BUTTON))
        self.hb.pack_end(self.menu['tools'])

        self.menu['preview'] = Gtk.Button()
        self.menu['preview'].add(Gtk.Image.new_from_icon_name(
            'utext-not-preview',
            Gtk.IconSize.BUTTON))
        self.menu['preview'].connect('clicked',
                                     self.on_toolbar_clicked, 'preview')
        self.hb.pack_end(self.menu['preview'])

        self.menu['search'] = Gtk.Button()
        self.menu['search'].add(Gtk.Image.new_from_icon_name(
            'utext-search',
            Gtk.IconSize.BUTTON))
        self.hb.pack_end(self.menu['search'])

        self.menu['save'] = Gtk.Button()
        self.menu['save'].add(Gtk.Label(_('Save')))
        self.hb.pack_end(self.menu['save'])
        '''
        self.menu['edit'] = Gtk.MenuButton()
        self.menu['edit'].add(Gtk.Image.new_from_gicon(
            Gio.ThemedIcon.new_with_default_fallbacks(
                'text-editor-symbolic'),
            Gtk.IconSize.BUTTON))
        self.hb.pack_start(self.menu['edit'])
        self.menu['view'] = Gtk.MenuButton()
        self.menu['view'].add(Gtk.Image.new_from_gicon(
            Gio.ThemedIcon.new_with_default_fallbacks(
                'view-paged-symbolic'),
            Gtk.IconSize.BUTTON))
        self.hb.pack_start(self.menu['view'])
        self.menu['search'] = Gtk.MenuButton()
        self.menu['search'].add(Gtk.Image.new_from_gicon(
            Gio.ThemedIcon.new_with_default_fallbacks(
                'edit-find-symbolic'),
            Gtk.IconSize.BUTTON))
        self.hb.pack_start(self.menu['search'])
        self.menu['format'] = Gtk.MenuButton()
        self.menu['format'].add(Gtk.Image.new_from_gicon(
            Gio.ThemedIcon.new_with_default_fallbacks(
                'format-justify-left-symbolic'),
            Gtk.IconSize.BUTTON))
        self.hb.pack_start(self.menu['format'])
        self.menu['insert'] = Gtk.MenuButton()
        self.menu['insert'].add(Gtk.Image.new_from_gicon(
            Gio.ThemedIcon.new_with_default_fallbacks(
                'insert-object-symbolic'),
            Gtk.IconSize.BUTTON))
        self.hb.pack_start(self.menu['insert'])
        self.menu['tools'] = Gtk.MenuButton()
        self.menu['tools'].add(Gtk.Image.new_from_gicon(
            Gio.ThemedIcon.new_with_default_fallbacks(
                'preferences-system-symbolic'),
            Gtk.IconSize.BUTTON))
        self.hb.pack_start(self.menu['tools'])
        self.menu['about'] = Gtk.MenuButton()
        self.menu['about'].add(
            Gtk.Image.new_from_gicon(
                Gio.ThemedIcon.new_with_default_fallbacks(
                    'dialog-information-symbolic'),
                Gtk.IconSize.BUTTON))
        self.hb.pack_end(self.menu['about'])


        self.menu['edit.menu'] = Gio.Menu()
        self.menu['edit'].set_menu_model(self.menu['edit.menu'])
        self.menu['edit.menu.01'] = Gio.Menu()
        self.menu['edit.menu'].append_section(None, self.menu['edit.menu.01'])
        self.menu['edit.menu.01.undo'] = Gio.MenuItem.new(
            _('Undo'), 'app.undo')

        self.menu['edit.menu.01.redo'] = Gio.MenuItem.new(
            _('Redo'), 'app.redo')
        self.menu['edit.menu.01'].append_item(
            self.menu['edit.menu.01.undo'])
        self.menu['edit.menu.01'].append_item(
            self.menu['edit.menu.01.redo'])
        self.menu['edit.menu.02'] = Gio.Menu()
        self.menu['edit.menu'].append_section(None, self.menu['edit.menu.02'])
        self.menu['edit.menu.02.cut'] = Gio.MenuItem.new(
            _('Cut'), 'app.cut')
        self.menu['edit.menu.02.copy'] = Gio.MenuItem.new(
            _('Copy'), 'app.copy')
        self.menu['edit.menu.02.paste'] = Gio.MenuItem.new(
            _('Paste'), 'app.paste')
        self.menu['edit.menu.02.remove'] = Gio.MenuItem.new(
            _('Remove'), 'app.remove')
        self.menu['edit.menu.02'].append_item(
            self.menu['edit.menu.02.cut'])
        self.menu['edit.menu.02'].append_item(
            self.menu['edit.menu.02.copy'])
        self.menu['edit.menu.02'].append_item(
            self.menu['edit.menu.02.paste'])
        self.menu['edit.menu.02'].append_item(
            self.menu['edit.menu.02.remove'])
        self.menu['edit.menu.03'] = Gio.Menu()
        self.menu['edit.menu'].append_section(None, self.menu['edit.menu.03'])
        self.menu['edit.menu.03.select_all'] = Gio.MenuItem.new(
            _('Select all'), 'app.select_all')
        self.menu['edit.menu.03'].append_item(
            self.menu['edit.menu.03.select_all'])
        self.menu['edit.menu.04'] = Gio.Menu()
        self.menu['edit.menu'].append_section(None, self.menu['edit.menu.04'])
        self.menu['edit.menu.04.lowercase'] = Gio.MenuItem.new(
            _('Convert selection to lowercase'), 'app.lowercase')
        self.menu['edit.menu.04'].append_item(
            self.menu['edit.menu.04.lowercase'])
        self.menu['edit.menu.04.titlecase'] = Gio.MenuItem.new(
            _('Convert selection to titlecase'), 'app.titlecase')
        self.menu['edit.menu.04'].append_item(
            self.menu['edit.menu.04.titlecase'])
        self.menu['edit.menu.04.uppercase'] = Gio.MenuItem.new(
            _('Convert selection to uppercase'), 'app.uppercase')
        self.menu['edit.menu.04'].append_item(
            self.menu['edit.menu.04.uppercase'])
        self.menu['edit.menu.05'] = Gio.Menu()
        self.menu['edit.menu'].append_section(None, self.menu['edit.menu.05'])
        self.menu['edit.menu.05.copy_selection_to_html'] = Gio.MenuItem.new(
            _('Copy selection to html'), 'app.copy_selection_to_html')
        self.menu['edit.menu.05'].append_item(
            self.menu['edit.menu.05.copy_selection_to_html'])
        self.menu['edit.menu.05.copy_all_to_html'] = Gio.MenuItem.new(
            _('Copy all to html'), 'app.copy_all_to_html')
        self.menu['edit.menu.05'].append_item(
            self.menu['edit.menu.05.copy_all_to_html'])
        self.menu['edit.menu.06'] = Gio.Menu()
        self.menu['edit.menu'].append_section(None, self.menu['edit.menu.06'])
        self.menu['edit.menu.06.preferences'] = Gio.MenuItem.new(
            _('Preferences'), 'app.preferences')
        self.menu['edit.menu.06'].append_item(
            self.menu['edit.menu.06.preferences'])

        self.menu['view.menu'] = Gio.Menu()
        self.menu['view'].set_menu_model(self.menu['view.menu'])
        self.menu['view.menu.01'] = Gio.Menu()
        self.menu['view.menu'].append_section(None, self.menu['view.menu.01'])
        self.menu['view.menu.01.html'] = Gio.MenuItem.new(
            _('Html'), 'app.html')
        self.menu['view.menu.01'].append_item(
            self.menu['view.menu.01.html'])
        self.menu['view.menu.02'] = Gio.Menu()
        self.menu['view.menu'].append_section(None, self.menu['view.menu.02'])
        self.menu['view.menu.02.hide_preview'] = Gio.MenuItem.new(
            _('Hide preview'), 'app.hide_preview')
        self.menu['view.menu.02'].append_item(
            self.menu['view.menu.02.hide_preview'])
        self.menu['view.menu.02.hide_status_bar'] = Gio.MenuItem.new(
            _('Hide status bar'), 'app.hide_status_bar')
        self.menu['view.menu.02'].append_item(
            self.menu['view.menu.02.hide_status_bar'])
        self.menu['view.menu.02.hide_toolbar'] = Gio.MenuItem.new(
            _('Hide toolbar'), 'app.hide_toolbar')
        self.menu['view.menu.02'].append_item(
            self.menu['view.menu.02.hide_toolbar'])
        self.menu['view.menu.03'] = Gio.Menu()
        self.menu['view.menu'].append_section(None, self.menu['view.menu.03'])
        self.menu['view.menu.03.night_mode'] = Gio.MenuItem.new(
            _('Night mode'), 'app.night_mode')
        self.menu['view.menu.03'].append_item(
            self.menu['view.menu.03.night_mode'])
        self.menu['view.menu.04'] = Gio.Menu()
        self.menu['view.menu'].append_section(None, self.menu['view.menu.04'])
        self.menu['view.menu.04.fullscreen'] = Gio.MenuItem.new(
            _('Fullscreen'), 'app.fullscreen')
        self.menu['view.menu.04'].append_item(
            self.menu['view.menu.04.fullscreen'])

        self.menu['search.menu'] = Gio.Menu()
        self.menu['search'].set_menu_model(self.menu['search.menu'])
        self.menu['search.menu.01'] = Gio.Menu()
        self.menu['search.menu'].append_section(None,
                                                self.menu['search.menu.01'])
        self.menu['search.menu.01.search'] = Gio.MenuItem.new(
            _('Search ...'), 'app.search')
        self.menu['search.menu.01'].append_item(
            self.menu['search.menu.01.search'])
        self.menu['search.menu.01.search_and_replace'] = Gio.MenuItem.new(
            _('Search and replace ...'), 'app.search_and_replace')
        self.menu['search.menu.01'].append_item(
            self.menu['search.menu.01.search_and_replace'])
        self.menu['search.menu.01.remove_highlight'] = Gio.MenuItem.new(
            _('Remove highlight'), 'app.remove_highlight')
        self.menu['search.menu.01'].append_item(
            self.menu['search.menu.01.remove_highlight'])


        self.menu['about.menu'] = Gio.Menu()
        self.menu['about'].set_menu_model(self.menu['about.menu'])
        self.menu['about.menu.01'] = Gio.Menu()
        self.menu['about.menu'].append_section(
            None, self.menu['about.menu.01'])
        self.menu['about.menu.01.goto_homepage'] = Gio.MenuItem.new(
            _('Homepage'), 'app.goto_homepage')
        self.menu['about.menu.01'].append_item(
            self.menu['about.menu.01.goto_homepage'])
        self.menu['about.menu.01.goto_bug'] = Gio.MenuItem.new(
            _('Report a bug'), 'app.goto_bug')
        self.menu['about.menu.01'].append_item(
            self.menu['about.menu.01.goto_bug'])
        self.menu['about.menu.01.goto_sugestion'] = Gio.MenuItem.new(
            _('Make a suggestion'), 'app.goto_sugestion')
        self.menu['about.menu.01'].append_item(
            self.menu['about.menu.01.goto_sugestion'])
        self.menu['about.menu.01.goto_translation'] = Gio.MenuItem.new(
            _('Translate this application'), 'app.goto_translation')
        self.menu['about.menu.01'].append_item(
            self.menu['about.menu.01.goto_translation'])
        self.menu['about.menu.01.goto_translation'] = Gio.MenuItem.new(
            _('Get help online'), 'app.goto_sugestion')
        self.menu['about.menu.02'] = Gio.Menu()
        self.menu['about.menu'].append_section(
            None, self.menu['about.menu.02'])
        self.menu['about.menu.02.goto_twitter'] = Gio.MenuItem.new(
            _('Follow me on Twitter'), 'app.goto_twitter')
        self.menu['about.menu.02'].append_item(
            self.menu['about.menu.02.goto_twitter'])
        self.menu['about.menu.02.goto_facebook'] = Gio.MenuItem.new(
            _('Follow me on Facebook'), 'app.goto_facebook')
        self.menu['about.menu.02'].append_item(
            self.menu['about.menu.02.goto_facebook'])
        self.menu['about.menu.02.goto_google_plus'] = Gio.MenuItem.new(
            _('Follow me on Google+'), 'app.goto_google_plus')
        self.menu['about.menu.02'].append_item(
            self.menu['about.menu.02.goto_google_plus'])
        self.menu['about.menu.03'] = Gio.Menu()
        self.menu['about.menu'].append_section(
            None, self.menu['about.menu.03'])
        self.menu['about.menu.03.goto_donate'] = Gio.MenuItem.new(
            _('Donate'), 'app.goto_donate')
        self.menu['about.menu.03'].append_item(
            self.menu['about.menu.03.goto_donate'])
        self.menu['about.menu.04'] = Gio.Menu()
        self.menu['about.menu'].append_section(
            None, self.menu['about.menu.04'])
        self.menu['about.menu.04.about'] = Gio.MenuItem.new(
            _('About...'), 'app.about')
        self.menu['about.menu.04.about'].set_attribute_value("accel", GLib.Variant("s", "<Alt>Z"))
        self.menu['about.menu.04'].append_item(
            self.menu['about.menu.04.about'])
        '''
    def on_button_clicked(self, widget):
        self.popover.show_all()

    def init_menu(self):
        menubar = Gtk.MenuBar()
        self.vbox.pack_start(menubar, False, False, 0)
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        ################################################################
        self.filemenu = Gtk.Menu.new()
        self.filem = Gtk.MenuItem.new_with_label(_('File'))
        self.filem.set_submenu(self.filemenu)
        #
        self.menus = {}
        #
        self.menus['new'] = Gtk.ImageMenuItem.new_with_label(_('New file'))
        self.menus['new'].connect('activate', self.on_toolbar_clicked, 'new')
        self.menus['new'].add_accelerator(
            'activate', accel_group, ord('N'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.filemenu.append(self.menus['new'])
        #
        self.filemenu.append(Gtk.SeparatorMenuItem())
        #
        self.menus['open'] = Gtk.ImageMenuItem.new_with_label(_('Open'))
        self.menus['open'].connect('activate', self.on_toolbar_clicked, 'open')
        self.menus['open'].add_accelerator(
            'activate', accel_group, ord('O'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.filemenu.append(self.menus['open'])
        #
        self.menus['close'] = Gtk.ImageMenuItem.new_with_label(_('Close'))
        self.menus['close'].connect(
            'activate', self.on_toolbar_clicked, 'close')
        self.menus['close'].add_accelerator(
            'activate', accel_group, ord('Q'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.filemenu.append(self.menus['close'])
        #
        menurecents = Gtk.Menu.new()
        self.recents = Gtk.MenuItem.new_with_label(_('Recent files...'))
        self.recents.set_submenu(menurecents)
        self.filemenu.append(self.recents)
        #
        self.filerecents = {}
        self.filerecents['file1'] = Gtk.MenuItem.new_with_label('file1')
        self.filerecents['file1'].connect('activate', self.on_menu_file_open)
        self.filerecents['file1'].set_visible(False)
        menurecents.append(self.filerecents['file1'])
        self.filerecents['file2'] = Gtk.MenuItem.new_with_label('file2')
        self.filerecents['file2'].connect('activate', self.on_menu_file_open)
        self.filerecents['file2'].set_visible(False)
        menurecents.append(self.filerecents['file2'])
        self.filerecents['file3'] = Gtk.MenuItem.new_with_label('file3')
        self.filerecents['file3'].connect('activate', self.on_menu_file_open)
        self.filerecents['file3'].set_visible(False)
        menurecents.append(self.filerecents['file3'])
        self.filerecents['file4'] = Gtk.MenuItem.new_with_label('file4')
        self.filerecents['file4'].connect('activate', self.on_menu_file_open)
        self.filerecents['file4'].set_visible(False)
        menurecents.append(self.filerecents['file4'])
        #
        self.filemenu.append(Gtk.SeparatorMenuItem())
        #
        self.menus['open_from_dropbox'] = Gtk.ImageMenuItem.new_with_label(
            _('Open from Dropbox'))
        self.menus['open_from_dropbox'].connect(
            'activate', self.on_toolbar_clicked, 'open_from_dropbox')
        self.filemenu.append(self.menus['open_from_dropbox'])
        self.menus['open_from_drive'] = Gtk.ImageMenuItem.new_with_label(
            _('Open from Google Drive'))
        self.menus['open_from_drive'].connect(
            'activate', self.on_toolbar_clicked, 'open_from_drive')
        self.filemenu.append(self.menus['open_from_drive'])
        #
        self.filemenu.append(Gtk.SeparatorMenuItem())
        #
        self.menus['save'] = Gtk.ImageMenuItem.new_with_label(_('Save'))
        self.menus['save'].connect(
            'activate', self.on_toolbar_clicked, 'save')
        self.menus['save'].add_accelerator(
            'activate', accel_group, ord('S'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.filemenu.append(self.menus['save'])
        #
        self.menus['save_as'] = Gtk.ImageMenuItem.new_with_label(_('Save as'))
        self.menus['save_as'].connect(
            'activate', self.on_toolbar_clicked, 'save_as')
        self.menus['save_as'].add_accelerator(
            'activate', accel_group, ord('S'),
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK,
            Gtk.AccelFlags.VISIBLE)
        self.filemenu.append(self.menus['save_as'])
        #
        self.filemenu.append(Gtk.SeparatorMenuItem())
        #
        menuexport = Gtk.Menu.new()
        self.export = Gtk.MenuItem.new_with_label(_('Export to...'))
        self.export.set_submenu(menuexport)
        self.filemenu.append(self.export)
        #
        self.exports = {}
        for exportformat in EXPORT_FORMATS:
            self.exports[exportformat['typeof']] = Gtk.MenuItem.new_with_label(
                exportformat['name'])
            self.exports[exportformat['typeof']].connect(
                'activate', self.on_menu_export, exportformat)
            self.exports[exportformat['typeof']].set_visible(False)
            menuexport.append(self.exports[exportformat['typeof']])
        #
        self.filemenu.append(Gtk.SeparatorMenuItem())
        #
        self.menus['save_on_dropbox'] = Gtk.ImageMenuItem.new_with_label(
            _('Save on Dropbox'))
        self.menus['save_on_dropbox'].connect(
            'activate', self.on_toolbar_clicked, 'save_on_dropbox')
        self.filemenu.append(self.menus['save_on_dropbox'])
        #
        self.menus['save_on_drive'] = Gtk.ImageMenuItem.new_with_label(
            _('Save on Google Drive'))
        self.menus['save_on_drive'].connect(
            'activate', self.on_toolbar_clicked, 'save_on_drive')
        self.filemenu.append(self.menus['save_on_drive'])
        #
        self.filemenu.append(Gtk.SeparatorMenuItem())
        #
        sal = Gtk.ImageMenuItem.new_with_label(_('Exit'))
        sal.connect('activate', self.on_toolbar_clicked, 'exit')
        sal.add_accelerator(
            'activate', accel_group, ord('Q'),
            Gdk.ModifierType.CONTROL_MASK,
            Gtk.AccelFlags.VISIBLE)
        self.filemenu.append(sal)
        #
        menubar.append(self.filem)
        ################################################################
        ################################################################
        self.fileedit = Gtk.Menu.new()
        self.filee = Gtk.MenuItem.new_with_label(_('Edit'))
        self.filee.set_submenu(self.fileedit)
        #
        self.menus['undo'] = Gtk.ImageMenuItem.new_with_label(_('Undo'))
        self.menus['undo'].connect(
            'activate', self.on_toolbar_clicked, 'undo')
        self.menus['undo'].add_accelerator(
            'activate', accel_group, ord('Z'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileedit.append(self.menus['undo'])
        #
        self.menus['redo'] = Gtk.ImageMenuItem.new_with_label(_('Redo'))
        self.menus['redo'].connect('activate', self.on_toolbar_clicked, 'redo')
        self.menus['redo'].add_accelerator(
            'activate', accel_group, ord('Y'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileedit.append(self.menus['redo'])
        #
        self.fileedit.append(Gtk.SeparatorMenuItem())
        #
        self.menus['cut'] = Gtk.ImageMenuItem.new_with_label(_('Cut'))
        self.menus['cut'].connect('activate', self.on_toolbar_clicked, 'cut')
        self.menus['cut'].add_accelerator(
            'activate', accel_group, ord('X'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileedit.append(self.menus['cut'])
        #
        self.menus['copy'] = Gtk.ImageMenuItem.new_with_label(_('Copy'))
        self.menus['copy'].connect('activate', self.on_toolbar_clicked, 'copy')
        self.menus['copy'].add_accelerator(
            'activate', accel_group, ord('C'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileedit.append(self.menus['copy'])
        #
        self.menus['paste'] = Gtk.ImageMenuItem.new_with_label(_('Paste'))
        self.menus['paste'].connect(
            'activate', self.on_toolbar_clicked, 'paste')
        self.menus['paste'].add_accelerator(
            'activate', accel_group, ord('V'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileedit.append(self.menus['paste'])
        #
        self.menus['remove'] = Gtk.ImageMenuItem.new_with_label(_('Remove'))
        self.menus['remove'].connect(
            'activate', self.on_toolbar_clicked, 'remove')
        self.fileedit.append(self.menus['remove'])
        #
        self.fileedit.append(Gtk.SeparatorMenuItem())
        #
        self.menus['select_all'] = Gtk.ImageMenuItem.new_with_label(
            _('Select All'))
        self.menus['select_all'].connect(
            'activate', self.on_toolbar_clicked, 'select_all')
        self.menus['select_all'].add_accelerator(
            'activate', accel_group, ord('A'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileedit.append(self.menus['select_all'])
        #
        self.fileedit.append(Gtk.SeparatorMenuItem())
        #
        self.menus['lowercase'] = Gtk.ImageMenuItem.new_with_label(
            _('Convert selection to lowercase'))
        self.menus['lowercase'].connect(
            'activate', self.on_toolbar_clicked, 'lowercase')
        self.fileedit.append(self.menus['lowercase'])
        #
        self.menus['titlecase'] = Gtk.ImageMenuItem.new_with_label(
            _('Convert selection to titlecase'))
        self.menus['titlecase'].connect(
            'activate', self.on_toolbar_clicked, 'titlecase')
        self.fileedit.append(self.menus['titlecase'])
        #
        self.menus['uppercase'] = Gtk.ImageMenuItem.new_with_label(
            _('Convert selection to uppercase'))
        self.menus['uppercase'].connect(
            'activate', self.on_toolbar_clicked, 'uppercase')
        self.fileedit.append(self.menus['uppercase'])
        #
        self.fileedit.append(Gtk.SeparatorMenuItem())
        #
        self.menus['selection_to_html'] = Gtk.ImageMenuItem.new_with_label(
            _('Copy selection to html'))
        self.menus['selection_to_html'].connect(
            'activate', self.on_toolbar_clicked, 'selection_to_html')
        self.fileedit.append(self.menus['selection_to_html'])
        #
        self.menus['all_to_html'] = Gtk.ImageMenuItem.new_with_label(
            _('Copy all to html'))
        self.menus['all_to_html'].connect(
            'activate', self.on_toolbar_clicked, 'all_to_html')
        self.fileedit.append(self.menus['all_to_html'])
        #
        self.fileedit.append(Gtk.SeparatorMenuItem())
        #
        self.pref = Gtk.ImageMenuItem.new_with_label(_('Preferences'))
        self.pref.set_image(
            Gtk.Image.new_from_stock(Gtk.STOCK_PREFERENCES, Gtk.IconSize.MENU))
        self.pref.connect('activate', self.on_toolbar_clicked, 'preferences')
        self.pref.set_always_show_image(True)
        self.fileedit.append(self.pref)
        #
        menubar.append(self.filee)
        ################################################################
        self.fileview = Gtk.Menu.new()
        self.filev = Gtk.MenuItem.new_with_label(_('View'))
        self.filev.set_submenu(self.fileview)
        #
        self.menus['preview_or_html'] = Gtk.MenuItem.new_with_label(
            _('Preview'))
        self.menus['preview_or_html'].connect(
            'activate', self.on_activate_preview_or_html)
        self.menus['preview_or_html'].add_accelerator(
            'activate', accel_group, ord('V'),
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK,
            Gtk.AccelFlags.VISIBLE)
        self.fileview.append(self.menus['preview_or_html'])
        #
        self.fileview.append(Gtk.SeparatorMenuItem())
        #
        self.menus['preview'] = Gtk.MenuItem.new_with_label(_('Hide preview'))
        self.menus['preview'].connect(
            'activate', self.on_toolbar_clicked, 'preview')
        self.fileview.append(self.menus['preview'])
        #
        self.menus['statusbar'] = Gtk.MenuItem.new_with_label(
            _('Hide status bar'))
        self.menus['statusbar'].connect(
            'activate', self.on_toolbar_clicked, 'statusbar')
        self.fileview.append(self.menus['statusbar'])
        #
        self.menus['toolbar'] = Gtk.MenuItem.new_with_label(_('Hide Toolbar'))
        self.menus['toolbar'].connect(
            'activate', self.on_toolbar_clicked, 'toolbar')
        self.fileview.append(self.menus['toolbar'])
        #
        self.fileview.append(Gtk.SeparatorMenuItem())
        #
        self.menus['nightmode'] = Gtk.MenuItem.new_with_label(
            _('Night mode'))
        self.menus['nightmode'].connect(
            'activate', self.on_toolbar_clicked, 'nightmode')
        self.fileview.append(self.menus['nightmode'])
        #
        self.fileview.append(Gtk.SeparatorMenuItem())
        #
        self.menus['fullscreen'] = Gtk.MenuItem.new_with_label(
            _('Full screen'))
        self.menus['fullscreen'].connect(
            'activate', self.on_toolbar_clicked, 'fullscreen')
        keyval, mask = Gtk.accelerator_parse('F11')
        self.menus['fullscreen'].add_accelerator(
            'activate', accel_group, keyval, mask, Gtk.AccelFlags.VISIBLE)
        self.fileview.append(self.menus['fullscreen'])
        #
        menubar.append(self.filev)
        ################################################################
        self.filesearch = Gtk.Menu.new()
        self.filess = Gtk.MenuItem.new_with_label(_('Search'))
        self.filess.set_submenu(self.filesearch)
        #
        self.menus['search'] = Gtk.MenuItem.new_with_label(_('Search') + '...')
        self.menus['search'].connect(
            'activate', self.on_toolbar_clicked, 'search')
        self.menus['search'].add_accelerator(
            'activate', accel_group, ord('F'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.filesearch.append(self.menus['search'])
        #
        self.menus['removehighlight'] = Gtk.MenuItem.new_with_label(
            _('Remove highlight') + '...')
        self.menus['removehighlight'].connect(
            'activate', self.on_toolbar_clicked, 'removehighlight')
        self.menus['removehighlight'].add_accelerator(
            'activate', accel_group, ord('K'),
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK,
            Gtk.AccelFlags.VISIBLE)
        self.filesearch.append(self.menus['removehighlight'])
        #
        self.filesearch.append(Gtk.SeparatorMenuItem())
        #
        self.menus['searchandreplace'] = Gtk.MenuItem.new_with_label(
            _('Search and replace') + '...')
        self.menus['searchandreplace'].connect(
            'activate', self.on_toolbar_clicked, 'searchandreplace')
        self.menus['searchandreplace'].add_accelerator(
            'activate', accel_group, ord('H'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.filesearch.append(self.menus['searchandreplace'])
        #
        menubar.append(self.filess)
        ################################################################
        self.formats = {}
        self.fileformat = Gtk.Menu.new()
        self.filef = Gtk.MenuItem.new_with_label(_('Format'))
        self.filef.set_submenu(self.fileformat)
        #
        self.formats['bold'] = Gtk.ImageMenuItem.new_with_label(_('Bold'))
        self.formats['bold'].connect(
            'activate', self.on_toolbar_clicked, 'bold')
        self.formats['bold'].add_accelerator(
            'activate', accel_group, ord('B'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['bold'])
        #
        self.formats['italic'] = Gtk.ImageMenuItem.new_with_label(
            _('Italic'))
        self.formats['italic'].connect(
            'activate', self.on_toolbar_clicked, 'italic')
        self.formats['italic'].add_accelerator(
            'activate', accel_group, ord('I'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['italic'])
        #
        self.formats['underline'] = Gtk.ImageMenuItem.new_with_label(
            _('Underline'))
        self.formats['underline'].connect(
            'activate', self.on_toolbar_clicked, 'underline')
        self.formats['underline'].add_accelerator(
            'activate', accel_group, ord('U'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['underline'])
        #
        self.formats['strikethrough'] = Gtk.ImageMenuItem.new_with_label(
            _('Strikethrough'))
        self.formats['strikethrough'].connect(
            'activate', self.on_toolbar_clicked, 'strikethrough')
        self.formats['strikethrough'].add_accelerator(
            'activate', accel_group, ord('D'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['strikethrough'])
        #
        self.formats['highlight'] = Gtk.ImageMenuItem.new_with_label(
            _('Highlight'))
        self.formats['highlight'].connect(
            'activate', self.on_toolbar_clicked, 'highlight')
        self.formats['highlight'].add_accelerator(
            'activate', accel_group, ord('H'),
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK,
            Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['highlight'])
        #
        self.formats['subscript'] = Gtk.ImageMenuItem.new_with_label(
            _('Subscript'))
        self.formats['subscript'].connect(
            'activate', self.on_toolbar_clicked, 'subscript')
        self.formats['subscript'].add_accelerator(
            'activate', accel_group, ord('-'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['subscript'])
        #
        self.formats['superscript'] = Gtk.ImageMenuItem.new_with_label(
            _('Superscript'))
        self.formats['superscript'].connect(
            'activate', self.on_toolbar_clicked, 'superscript')
        self.formats['superscript'].add_accelerator(
            'activate', accel_group, ord('+'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['superscript'])
        #
        self.fileformat.append(Gtk.SeparatorMenuItem())
        #
        self.formats['bullet_list'] = Gtk.ImageMenuItem.new_with_label(
            _('Bullet List'))
        self.formats['bullet_list'].connect(
            'activate', self.on_toolbar_clicked, 'bullet_list')
        self.fileformat.append(self.formats['bullet_list'])
        #
        self.formats['numbered_list'] = Gtk.ImageMenuItem.new_with_label(
            _('Numbered List'))
        self.formats['numbered_list'].connect(
            'activate', self.on_toolbar_clicked, 'numbered_list')
        self.fileformat.append(self.formats['numbered_list'])
        #
        self.fileformat.append(Gtk.SeparatorMenuItem())
        #
        self.formats['blockquote'] = Gtk.ImageMenuItem.new_with_label(
            _('Bloque Quote'))
        self.formats['blockquote'].connect(
            'activate', self.on_toolbar_clicked, 'blockquote')
        self.fileformat.append(self.formats['blockquote'])
        #
        self.formats['code'] = Gtk.ImageMenuItem.new_with_label(_('Code'))
        self.formats['code'].connect(
            'activate', self.on_toolbar_clicked, 'code')
        self.fileformat.append(self.formats['code'])
        #
        self.fileformat.append(Gtk.SeparatorMenuItem())
        #
        self.formats['title1'] = Gtk.ImageMenuItem.new_with_label(
            _('Heading One'))
        self.formats['title1'].connect(
            'activate', self.on_toolbar_clicked, 'title1')
        self.formats['title1'].add_accelerator(
            'activate', accel_group, ord('1'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['title1'])
        #
        self.formats['title2'] = Gtk.ImageMenuItem.new_with_label(
            _('Heading Two'))
        self.formats['title2'].connect(
            'activate', self.on_toolbar_clicked, 'title2')
        self.formats['title2'].add_accelerator(
            'activate', accel_group, ord('2'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['title2'])
        #
        self.formats['title3'] = Gtk.ImageMenuItem.new_with_label(
            _('Heading Three'))
        self.formats['title3'].connect(
            'activate', self.on_toolbar_clicked, 'title3')
        self.formats['title3'].add_accelerator(
            'activate', accel_group, ord('3'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['title3'])
        #
        self.formats['title4'] = Gtk.ImageMenuItem.new_with_label(
            _('Heading Four'))
        self.formats['title4'].connect(
            'activate', self.on_toolbar_clicked, 'title4')
        self.formats['title4'].add_accelerator(
            'activate', accel_group, ord('4'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['title4'])
        #
        self.formats['title5'] = Gtk.ImageMenuItem.new_with_label(
            _('Heading Five'))
        self.formats['title5'].connect(
            'activate', self.on_toolbar_clicked, 'title5')
        self.formats['title5'].add_accelerator(
            'activate', accel_group, ord('5'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['title5'])
        #
        self.formats['title6'] = Gtk.ImageMenuItem.new_with_label(
            _('Heading Six'))
        self.formats['title6'].connect(
            'activate', self.on_toolbar_clicked, 'title6')
        self.formats['title6'].add_accelerator(
            'activate', accel_group, ord('6'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileformat.append(self.formats['title6'])
        #
        menubar.append(self.filef)
        ################################################################
        self.inserts = {}
        self.fileinsert = Gtk.Menu.new()
        self.filei = Gtk.MenuItem.new_with_label(_('Insert'))
        self.filei.set_submenu(self.fileinsert)
        #
        self.inserts['rule'] = Gtk.ImageMenuItem.new_with_label(
            _('Insert Horizontal Rule'))
        self.inserts['rule'].connect(
            'activate', self.on_toolbar_clicked, 'rule')
        self.inserts['rule'].add_accelerator(
            'activate', accel_group, ord('H'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileinsert.append(self.inserts['rule'])
        #
        self.inserts['timestamp'] = Gtk.ImageMenuItem.new_with_label(
            _('Insert Timestamp'))
        self.inserts['timestamp'].connect(
            'activate', self.on_toolbar_clicked, 'timestamp')
        self.inserts['timestamp'].add_accelerator(
            'activate', accel_group, ord('T'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileinsert.append(self.inserts['timestamp'])
        #
        self.inserts['more'] = Gtk.ImageMenuItem.new_with_label(
            _('Insert more'))
        self.inserts['more'].connect(
            'activate', self.on_toolbar_clicked, 'more')
        self.inserts['more'].add_accelerator(
            'activate', accel_group, ord('M'),
            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.fileinsert.append(self.inserts['more'])
        #
        self.fileinsert.append(Gtk.SeparatorMenuItem())
        #
        self.inserts['image'] = Gtk.ImageMenuItem.new_with_label(
            _('Insert Image'))
        self.inserts['image'].connect(
            'activate', self.on_toolbar_clicked, 'image')
        self.inserts['image'].add_accelerator(
            'activate', accel_group, ord('I'),
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK,
            Gtk.AccelFlags.VISIBLE)
        self.fileinsert.append(self.inserts['image'])
        #
        self.inserts['url'] = Gtk.ImageMenuItem.new_with_label(_('Insert Url'))
        self.inserts['url'].connect('activate', self.on_toolbar_clicked, 'url')
        self.inserts['url'].add_accelerator(
            'activate', accel_group, ord('U'),
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK,
            Gtk.AccelFlags.VISIBLE)
        self.fileinsert.append(self.inserts['url'])
        #
        menubar.append(self.filei)
        ################################################################
        self.tools = {}
        self.filetool = Gtk.Menu.new()
        self.filet = Gtk.MenuItem.new_with_label(_('Tools'))
        self.filet.set_submenu(self.filetool)
        #
        self.tools['spellcheck'] = Gtk.CheckMenuItem.new_with_label(
            _('Spell check'))
        self.tools['spellcheck'].connect(
            'activate', self.on_toolbar_clicked, 'spellcheck')
        self.tools['spellcheck'].add_accelerator(
            'activate', accel_group, ord('S'),
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK,
            Gtk.AccelFlags.VISIBLE)
        self.filetool.append(self.tools['spellcheck'])
        #
        menubar.append(self.filet)
        ################################################################
        self.filehelp = Gtk.Menu.new()
        self.fileh = Gtk.MenuItem.new_with_label(_('Help'))
        self.fileh.set_submenu(self.get_help_menu())
        #
        menubar.append(self.fileh)

    def on_menu_export(self, widget, exportformat):
        dialog = Gtk.FileChooserDialog(
            _('Select a file to save to') + ' ' + exportformat['name'],
            self,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(self.preferences['last_dir'])
        filter = Gtk.FileFilter()
        filter.set_name(exportformat['name'].upper() + ' ' + _('files'))
        filter.add_mime_type(exportformat['mimetype'])
        filter.add_pattern('*.' + exportformat['extension'])
        dialog.add_filter(filter)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            if filename is None:
                return
            if not filename.endswith('.'+exportformat['extension']):
                filename += '.'+exportformat['extension']
            data = self.get_buffer_text()
            if data is not None:
                if exportformat['typeof'] == 'pdf':
                    options = {
                        'page-size': 'A4',
                        'margin-top': '20mm',
                        'margin-right': '15mm',
                        'margin-bottom': '20mm',
                        'margin-left': '25mm',
                        'encoding': 'utf-8',
                    }
                    html_content = self.md.convert(data)
                    data = '<html><head><meta charset="utf-8">'
                    data += '</head><body>'
                    data += unquote_plus(html_content)
                    data += '</body></html>'
                    pdfkit.from_string(
                        data, filename, options=options)
                else:
                    try:
                        extra_args = (
                                      '--smart',
                                      '--standalone',
                                      )
                        output = pypandoc.convert(
                            data,  # source=tmpf.name,
                            to=exportformat['typeof'],
                            format='md',
                            outputfile=filename,
                            extra_args=extra_args)
                    except Exception as e:
                        print(e)
        else:
            dialog.destroy()

    def on_activate_preview_or_html(self, widget):
        if self.menus['preview_or_html'].get_label() == _('Preview'):
            self.menus['preview_or_html'].set_label(_('Html'))
            self.show_source_code(False)
        else:
            self.menus['preview_or_html'].set_label(_('Preview'))
            self.show_source_code(True)

    def get_help_menu(self):
        help_menu = Gtk.Menu()
        #
        add2menu(
            help_menu,
            text=_('Web...'),
            conector_event='activate',
            conector_action=lambda x:
            webbrowser.open('https://launchpad.net/utext'))
        add2menu(
            help_menu,
            text=_('Get help online...'),
            conector_event='activate',
            conector_action=lambda x:
            webbrowser.open('https://answers.launchpad.net/utext'))
        add2menu(
            help_menu,
            text=_('Translate this application...'),
            conector_event='activate',
            conector_action=lambda x:
            webbrowser.open('https://translations.launchpad.net/utext'))
        add2menu(
            help_menu,
            text=_('Report a bug...'),
            conector_event='activate',
            conector_action=lambda x:
            webbrowser.open('https://bugs.launchpad.net/utext'))
        add2menu(help_menu)
        web = add2menu(
            help_menu,
            text=_('Homepage'),
            conector_event='activate',
            conector_action=lambda x:
            webbrowser.open('http://www.atareao.es/tag/utext'))
        twitter = add2menu(
            help_menu,
            text=_('Follow us in Twitter'),
            conector_event='activate',
            conector_action=lambda x:
            webbrowser.open('https://twitter.com/atareao'))
        googleplus = add2menu(
            help_menu,
            text=_('Follow us in Google+'),
            conector_event='activate',
            conector_action=lambda x: webbrowser.open(
                'https://plus.google.com/118214486317320563625/posts'))
        facebook = add2menu(
            help_menu,
            text=_('Follow us in Facebook'),
            conector_event='activate',
            conector_action=lambda x:
            webbrowser.open('http://www.facebook.com/elatareao'))
        add2menu(help_menu)
        add2menu(
            help_menu,
            text=_('About'),
            conector_event='activate',
            conector_action=self.on_about_activate)
        #
        web.set_image(
            Gtk.Image.new_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_size(
                    os.path.join(comun.SOCIALDIR, 'web.svg'), 24, 24)))
        web.set_always_show_image(True)
        twitter.set_image(
            Gtk.Image.new_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_size(
                    os.path.join(comun.SOCIALDIR, 'twitter.svg'), 24, 24)))
        twitter.set_always_show_image(True)
        googleplus.set_image(
            Gtk.Image.new_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_size(
                    os.path.join(comun.SOCIALDIR, 'googleplus.svg'), 24, 24)))
        googleplus.set_always_show_image(True)
        facebook.set_image(
            Gtk.Image.new_from_pixbuf(
                GdkPixbuf.Pixbuf.new_from_file_at_size(
                    os.path.join(comun.SOCIALDIR, 'facebook.svg'), 24, 24)))
        facebook.set_always_show_image(True)
        #
        help_menu.show()
        return help_menu

    def add_filters(self, dialog):
        filter_text = Gtk.FileFilter()

        filter_markdown = Gtk.FileFilter()
        filter_markdown.set_name("Markdown ")
        filter_markdown.add_mime_type("text/x-markdown")
        dialog.add_filter(filter_markdown)

        filter_text.set_name("Plain text")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

    def init_template(self):
        self.md = Markdown(extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.abbr',
            'markdown.extensions.attr_list',
            'markdown.extensions.def_list',
            'markdown.extensions.fenced_code',
            'markdown.extensions.footnotes',
            'markdown.extensions.tables',
            'markdown.extensions.smart_strong',
            'markdown.extensions.admonition',
            'markdown.extensions.codehilite',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
            'markdown.extensions.smarty',
            'markdown.extensions.toc',
            'markdown.extensions.wikilinks',
            MathExtension(),
            MyExtension()
        ])
        # Jinja templates
        self.jt = env.get_template('header.html')

    def load_styles(self):
        self.style_provider = Gtk.CssProvider()
        css = open(os.path.join(comun.THEMESDIR, 'gtk.css'), 'rb')
        css_data = css.read()
        css.close()
        self.style_provider.load_from_data(css_data)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_buffer_changed(self, widget):
        self.emit('file-modified')
        self.menus['undo'].set_sensitive(self.writer.get_buffer().can_undo)
        self.buttons['undo'].set_sensitive(self.writer.get_buffer().can_undo)
        self.menus['redo'].set_sensitive(self.writer.get_buffer().can_redo)
        self.buttons['redo'].set_sensitive(self.writer.get_buffer().can_redo)
        if (self.number_of_lines != self.writer.get_buffer().get_line_count())\
                and self.preferences['autosave']:
            self.number_of_lines = self.writer.get_buffer().get_line_count()
            self.save_current_file()
        else:
            if not self.launched or self.launched is False:
                self.launched = True
                print('launched')
                GLib.timeout_add(300 * 1000,
                                 self.save_current_file_deferreaded)

        '''
        if self.timer is not None:
            self.timer.cancel()
        self.timer = threading.Timer(TIME_LAPSE, self.do_it)
        self.timer.start()
        '''

    def save_current_file_deferreaded(self):
        if self.is_saving:
            return False
        if self.preferences['autosave'] and\
                self.writer.get_buffer().get_modified():
            self.number_of_lines = self.writer.get_buffer().get_line_count()
            self.save_current_file()
            print('saved')
        self.launched = False
        return True

    def get_buffer_text(self):
        try:
            start_iter, end_iter = self.writer.get_buffer().get_bounds()
            text = self.writer.get_buffer().get_text(
                start_iter,
                end_iter, True)
            return text
        except Exception:
            print('--------------------------')
            print('Errrorrrr')
            print('--------------------------')
            pass
        return None

    def on_navigation2(self, web_view, frame, request, nav_action,
                      policy_decision, data=None):
        if request.get_uri() != '/':
            policy_decision.ignore()
        print(request.get_uri()[1:], request)
        print(web_view.get_dom_document().get_element_by_id(
            request.get_uri()[1:]))
        print(self.md.toc)
        pattern = r'<a\s*href=\"{0}\">([^<]+)</a>'.format(
            request.get_uri())
        matches = re.findall(pattern, self.md.toc)
        if matches is not None and len(matches) > 0:
            text_to_search = matches[0]
            ans = self.writer.get_buffer().get_start_iter().forward_search(
                text_to_search, 0, self.writer.get_buffer().get_end_iter())
            if ans is not None:
                self.writer.scroll_to_iter(ans[0], 0, True, 0, 0)
        '''

        self.search_and_mark(
            self.searched_text,
            self.writer.get_buffer().get_start_iter())
        self.writer.get_buffer().end_user_action()
        '''


    def on_navigation(self, web_view, frame, request, nav_action,
                      policy_decision, data=None):
        if request.get_uri() != '/':
            policy_decision.ignore()
            webbrowser.open(request.get_uri())

    def on_about_activate(self, widget):
        ad = Gtk.AboutDialog()
        ad.set_name(comun.APPNAME)
        ad.set_version(comun.VERSION)
        ad.set_copyright('Copyrignt (c) 2011-2018\nLorenzo Carbonell')
        ad.set_comments(_('An application to work with markdown'))
        ad.set_license('''
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
''')
        ad.set_website('http://www.atareao.es')
        ad.set_website_label('http://www.atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_documenters([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_translator_credits('\
Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>\n')
        ad.set_program_name('uText')
        ad.set_logo(GdkPixbuf.Pixbuf.new_from_file(comun.ICON))
        ad.run()
        ad.destroy()

    def on_close_application(self, widget, data):
        if self.writer.get_buffer().get_modified():
            dialog = Gtk.MessageDialog(
                self, 0,
                Gtk.MessageType.WARNING,
                Gtk.ButtonsType.OK_CANCEL,
                _('File modified'))
            dialog.format_secondary_text(_('Save file?'))
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.save_current_file()
            dialog.destroy()
        self.save_preferences()
        exit(0)

    def on_toolbar_clicked(self, widget, option):
        print(widget, option)
        if type(widget) == Gio.SimpleAction:
            option = widget.get_name()
        if option == 'new':
            self.writer.get_buffer().set_text('')
            self.load_file()
            if self.menus['preview_or_html'].get_label() == _('Html'):
                self.menus['preview_or_html'].set_label(_('Html'))
                self.show_source_code(False)
            else:
                self.menus['preview_or_html'].set_label(_('Preview'))
                self.show_source_code(True)
        elif option == 'undo':
            if self.writer.get_buffer().can_undo():
                self.writer.get_buffer().undo()
                self.do_it()
        elif option == 'redo':
            if self.writer.get_buffer().can_redo():
                self.writer.get_buffer().redo()
                self.do_it()
        elif option == 'open':
            self.load_file_dialog()
        elif option == 'close':
            self.save_current_file()
            self.current_filepath = None
            self.on_toolbar_clicked(None, 'new')
            self.fileDriveId = None
            self.fileDropboxId = None
            self.fileDrive = None
            self.fileDropbox = None
        elif option == 'open_from_dropbox':
            files = []
            ds = DropboxService(comun.TOKEN_FILE)
            if os.path.exists(comun.TOKEN_FILE) and ds.get_account_info():
                files = ds.get_files()
                if len(files) > 0:
                    result = []
                    for element in files:
                        afile = {}
                        afile['name'] = element['path'][1:]
                        result.append(afile)
                    cm = FilesInCloudDialog('Dropbox', result)
                    if cm.run() == Gtk.ResponseType.ACCEPT:
                        file_selected = cm.get_selected()
                        self.fileDropbox = file_selected['name']
                        self.fileDropboxId = -1
                        text_string = ds.get_file(self.fileDropbox)
                        if text_string is not None:
                            self.writer.get_buffer().set_text(text_string)
                    cm.destroy()
        elif option == 'open_from_drive':
            files = []
            ds = DriveService(comun.TOKEN_FILE_DRIVE)
            if os.path.exists(comun.TOKEN_FILE_DRIVE):
                files = ds.get_files()
                if len(files) > 0 and 'files' in files.keys() and\
                        len(files['files']) > 0:
                    result = []
                    for element in files['files']:
                        print(element)
                        result.append(element)
                    cm = FilesInCloudDialog('Drive', result)
                    if cm.run() == Gtk.ResponseType.ACCEPT:
                        file_selected = cm.get_selected()
                        print(file_selected)
                        self.fileDrive = file_selected['name']
                        self.fileDriveId = file_selected['id']
                        text_string = ds.get_file(file_selected['id'])
                        if text_string is not None:
                            self.writer.get_buffer().set_text(text_string)
                    cm.destroy()
        elif option == 'exit':
            self.on_close_application(widget, None)
        elif option == 'save':
            self.save_current_file()
        elif option == 'save_as':
            self.save_as()
        elif option == 'save_as_pdf':
            self.save_as_pdf()
        elif option == 'save_on_dropbox':
            if self.fileDropbox is None:
                dialog = FilenameDialog('Dropbox')
                if dialog.run() == Gtk.ResponseType.ACCEPT:
                    filename = dialog.get_filename()
                    dialog.destroy()
                    if not filename.endswith('.md'):
                        filename = filename + '.md'
                    self.fileDropbox = filename
                    self.fileDropboxId = -1
                else:
                    dialog.destroy()
                    return
            data = self.get_buffer_text()
            if data is not None:
                ds = DropboxService(comun.TOKEN_FILE)
                if os.path.exists(comun.TOKEN_FILE) and ds.get_account_info():
                    print(1)
                    print(ds.put_file(self.fileDropbox, data))
        elif option == 'save_on_drive':
            if self.fileDrive is None:
                dialog = FilenameDialog('Drive')
                if dialog.run() == Gtk.ResponseType.ACCEPT:
                    filename = dialog.get_filename()
                    dialog.destroy()
                    if not filename.endswith('.md'):
                        filename = filename + '.md'
                    self.fileDrive = filename
                else:
                    dialog.destroy()
                    return
            data = self.get_buffer_text()
            if data is not None:
                ds = DriveService(comun.TOKEN_FILE_DRIVE)
                if os.path.exists(comun.TOKEN_FILE_DRIVE):
                    if self.fileDriveId is not None:
                        ans = ds.update_file(self.fileDriveId,
                                             self.fileDrive,
                                             data)
                    else:
                        ans = ds.put_file(self.fileDrive, data)
                    if ans is not None:
                        self.fileDriveId = ans['id']
        elif option == 'search':
            searchDialog = SearchDialog(self.searched_text)
            if searchDialog.run() == Gtk.ResponseType.ACCEPT:
                searchDialog.hide()
                self.remove_all_tag(TAG_FOUND)
                self.searched_text = searchDialog.search_text.get_text()
                self.writer.get_buffer().begin_user_action()
                self.search_and_mark(
                    self.searched_text,
                    self.writer.get_buffer().get_start_iter())
                self.writer.get_buffer().end_user_action()
            searchDialog.destroy()
        elif option == 'removehighlight':
            self.writer.get_buffer().begin_user_action()
            self.remove_all_tag(TAG_FOUND)
            self.writer.get_buffer().end_user_action()
        elif option == 'searchandreplace':
            searchandreplaceDialog = SearchAndReplaceDialog(
                self.searched_text, self.replacement_text)
            if searchandreplaceDialog.run() == Gtk.ResponseType.ACCEPT:
                searchandreplaceDialog.hide()
                self.remove_all_tag(TAG_FOUND)
                self.searched_text =\
                    searchandreplaceDialog.search_text.get_text()
                self.replacement_text =\
                    searchandreplaceDialog.replace_text.get_text()
                self.writer.get_buffer().begin_user_action()
                self.search_and_replace(
                    self.searched_text,
                    self.replacement_text,
                    self.writer.get_buffer().get_start_iter())
                self.writer.get_buffer().end_user_action()
            searchandreplaceDialog.destroy()

        elif option == 'preview':

            if self.menus['preview'].get_label() == _('Show preview'):
                self.menus['preview'].set_label(_('Hide preview'))
                self.hpaned.get_child2().set_visible(True)
                self.menu['preview'].get_child().set_from_icon_name(
                    'utext-not-preview',
                    Gtk.IconSize.BUTTON)
                self.do_it()
            else:
                self.menus['preview'].set_label(_('Show preview'))
                self.hpaned.get_child2().set_visible(False)
                self.menu['preview'].get_child().set_from_icon_name(
                    'utext-preview',
                    Gtk.IconSize.BUTTON)
        elif option == 'fullscreen':
            if self.menus['fullscreen'].get_label() == _('Full screen'):
                self.fullscreen()
                self.menus['fullscreen'].set_label(_('Normal screen'))
            else:
                self.unfullscreen()
                self.menus['fullscreen'].set_label(_('Full screen'))
        elif option == 'zoom_100':
            self.webkit_viewer.set_zoom_level(1.0)
        elif option == 'zoom_in':
            self.webkit_viewer.zoom_in()
        elif option == 'zoom_out':
            self.webkit_viewer.zoom_out()
        elif option == 'nightmode':
            if self.menus['nightmode'].get_label() == _('Night mode'):
                self.menus['nightmode'].set_label(_('Day mode'))
                css_filename = os.path.join(
                    comun.THEMESDIR, 'gtk_night_mode.css')
            else:
                self.menus['nightmode'].set_label(_('Night mode'))
                css_filename = os.path.join(comun.THEMESDIR, 'gtk.css')
            css = open(css_filename, 'rb')
            css_data = css.read()
            css.close()
            self.style_provider = Gtk.CssProvider()
            self.style_provider.load_from_data(css_data)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), self.style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        elif option == 'preferences':
            cm = PreferencesDialog()
            if cm.run() == Gtk.ResponseType.ACCEPT:
                cm.close_ok()
                self.load_preferences()
                self.apply_preferences()
            cm.hide()
            cm.destroy()
        elif option == 'blockquote':
            self.writer.get_buffer().begin_user_action()
            self.insert_at_start_of_line('>')
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'code':
            self.writer.get_buffer().begin_user_action()
            self.wrap_text('\n```\n', '\n```\n')
            aniter = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            aniter.backward_chars(5)
            self.writer.get_buffer().place_cursor(aniter)
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'title1':
            self.insert_at_start_of_line('#')
            self.writer.grab_focus()
            self.do_it()
        elif option == 'title2':
            self.insert_at_start_of_line('##')
            self.writer.grab_focus()
            self.do_it()
        elif option == 'title3':
            self.insert_at_start_of_line('###')
            self.writer.grab_focus()
            self.do_it()
        elif option == 'title4':
            self.insert_at_start_of_line('####')
            self.writer.grab_focus()
            self.do_it()
        elif option == 'title5':
            self.insert_at_start_of_line('#####')
            self.writer.grab_focus()
            self.do_it()
        elif option == 'title6':
            self.insert_at_start_of_line('######')
            self.writer.grab_focus()
            self.do_it()
        elif option == 'bullet-list':
            self.insert_at_start_of_line('*')
            self.writer.grab_focus()
            self.do_it()
        elif option == 'numbered-list':
            data = self.get_first_n_characters_at_previous_line(3)
            if data.find('. ') > -1:
                number = data[:data.find('. ')]
            else:
                number = 0
            self.insert_at_start_of_line('%d.' % (int(number) + 1))
            self.writer.grab_focus()
            self.do_it()
        elif option == 'cut':
            self.writer.get_buffer().cut_clipboard(self.clipboard, True)
            self.writer.grab_focus()
            self.do_it()
        elif option == 'copy':
            self.writer.get_buffer().copy_clipboard(self.clipboard)
            self.writer.grab_focus()
        elif option == 'paste':
            self.writer.get_buffer().paste_clipboard(
                self.clipboard, None, True)
            self.writer.grab_focus()
            self.do_it()
        elif option == 'remove':
            bounds = self.writer.get_buffer().get_selection_bounds()
            if (bounds):
                iteratwordstart, iteratwordend = bounds
                self.writer.get_buffer().delete(iteratwordstart, iteratwordend)
            self.writer.grab_focus()
            self.do_it()
        elif option == 'select_all':
            start_iter = self.writer.get_buffer().get_start_iter()
            end_iter = self.writer.get_buffer().get_end_iter()
            self.writer.get_buffer().select_range(start_iter, end_iter)
        elif option == 'lowercase':
            bounds = self.writer.get_buffer().get_selection_bounds()
            if (bounds):
                iteratwordstart, iteratwordend = bounds
                text_string = self.writer.get_buffer().get_text(
                    iteratwordstart, iteratwordend, True)
                self.writer.get_buffer().begin_user_action()
                self.writer.get_buffer().delete(iteratwordstart, iteratwordend)
                self.writer.get_buffer().insert_at_cursor(text_string.lower())
                self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'titlecase':
            bounds = self.writer.get_buffer().get_selection_bounds()
            if (bounds):
                iteratwordstart, iteratwordend = bounds
                text_string = self.writer.get_buffer().get_text(
                    iteratwordstart, iteratwordend, True)
                self.writer.get_buffer().begin_user_action()
                self.writer.get_buffer().delete(iteratwordstart, iteratwordend)
                self.writer.get_buffer().insert_at_cursor(text_string.title())
                self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'uppercase':
            bounds = self.writer.get_buffer().get_selection_bounds()
            if (bounds):
                iteratwordstart, iteratwordend = bounds
                text_string = self.writer.get_buffer().get_text(
                    iteratwordstart, iteratwordend, True)
                self.writer.get_buffer().begin_user_action()
                self.writer.get_buffer().delete(iteratwordstart, iteratwordend)
                self.writer.get_buffer().insert_at_cursor(text_string.upper())
                self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'selection_to_html':
            bounds = self.writer.get_buffer().get_selection_bounds()
            if (bounds):
                iteratwordstart, iteratwordend = bounds
                text_string = self.writer.get_buffer().get_text(
                    iteratwordstart, iteratwordend, True)
                self.clipboard.set_text(self.md.convert(text_string), -1)
        elif option == 'all_to_html':
            iteratwordstart = self.writer.get_buffer().get_start_iter()
            iteratwordend = self.writer.get_buffer().get_end_iter()
            text_string = self.writer.get_buffer().get_text(
                iteratwordstart, iteratwordend, True)
            self.clipboard.set_text(self.md.convert(text_string), -1)
        elif option == 'statusbar':
            if self.statusbar.get_visible():
                self.statusbar.set_visible(False)
                self.menus['statusbar'].set_label(_('Show status bar'))
            else:
                self.statusbar.set_visible(True)
                self.menus['statusbar'].set_label(_('Hide status bar'))
        elif option == 'toolbar':
            if self.toolbar.get_visible():
                self.toolbar.set_visible(False)
                self.menus['toolbar'].set_label(_('Show Toolbar'))
            else:
                self.toolbar.set_visible(True)
                self.menus['toolbar'].set_label(_('Hide Toolbar'))
        elif option == 'bold':
            self.writer.get_buffer().begin_user_action()
            self.wrap_text('**', '**')
            aniter = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            aniter.backward_chars(2)
            self.writer.get_buffer().place_cursor(aniter)
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'italic':
            self.writer.get_buffer().begin_user_action()
            self.wrap_text('*', '*')
            aniter = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            aniter.backward_chars(1)
            self.writer.get_buffer().place_cursor(aniter)
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'strikethrough':
            self.writer.get_buffer().begin_user_action()
            self.wrap_text('~~', '~~')
            aniter = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            aniter.backward_chars(1)
            self.writer.get_buffer().place_cursor(aniter)
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'subscript':
            self.writer.get_buffer().begin_user_action()
            self.wrap_text('--', '--')
            aniter = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            aniter.backward_chars(2)
            self.writer.get_buffer().place_cursor(aniter)
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'superscript':
            self.writer.get_buffer().begin_user_action()
            self.wrap_text('++', '++')
            aniter = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            aniter.backward_chars(2)
            self.writer.get_buffer().place_cursor(aniter)
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'highlight':
            self.writer.get_buffer().begin_user_action()
            self.wrap_text('==', '==')
            aniter = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            aniter.backward_chars(2)
            self.writer.get_buffer().place_cursor(aniter)
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'underline':
            self.writer.get_buffer().begin_user_action()
            self.wrap_text('__', '__')
            aniter = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            aniter.backward_chars(2)
            self.writer.get_buffer().place_cursor(aniter)
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'insert-horizontal-line':
            self.writer.get_buffer().begin_user_action()
            self.insert_at_cursor('\n---\n')
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'insert-more':
            self.writer.get_buffer().begin_user_action()
            self.insert_at_cursor('\n<!--more-->\n')
            self.writer.get_buffer().end_user_action()
            self.writer.grab_focus()
            self.do_it()
        elif option == 'insert-image':
            cm = InsertImageDialog(self)
            if cm.run() == Gtk.ResponseType.ACCEPT:
                alt_text = cm.alt_text.get_text()
                title = cm.title.get_text()
                url = cm.url.get_text()
                if not url.startswith('http://') and not\
                        url.startswith('https://'):
                    url = 'http://' + url
                self.writer.get_buffer().begin_user_action()
                self.insert_at_cursor('![%s](%s  "%s")' % (
                    alt_text, url, title))
                self.writer.get_buffer().end_user_action()
                self.do_it()
            cm.hide()
            cm.destroy()
            self.writer.grab_focus()
        elif option == 'insert-link':
            cm = InsertUrlDialog(self)
            if cm.run() == Gtk.ResponseType.ACCEPT:
                alt_text = cm.alt_text.get_text()
                url = cm.url.get_text()
                if not url.startswith('http://') and not\
                        url.startswith('https://'):
                    url = 'http://' + url
                self.writer.get_buffer().begin_user_action()
                self.insert_at_cursor('[%s](%s)' % (alt_text, url))
                self.writer.get_buffer().end_user_action()
                self.do_it()
            cm.hide()
            cm.destroy()
            self.writer.grab_focus()
        elif option == 'insert-table':
            itd = InsertTableDialog(self)
            if itd.run() == Gtk.ResponseType.ACCEPT:
                rows = itd.rows.get_value_as_int()
                columns = itd.columns.get_value_as_int()
                header = '|' * columns + '|\n'
                defrows = '|---' * columns + '|\n'
                str_table = header + defrows + header * rows
                self.writer.get_buffer().begin_user_action()
                self.insert_at_cursor('\n' + str_table)
                self.writer.get_buffer().end_user_action()
                self.do_it()
                itd.destroy()
            else:
                itd.destroy()
            self.writer.grab_focus()
        elif option == 'create-table':
            tde = TableEditorDialog(self, 2, 2)
            if tde.run() == Gtk.ResponseType.ACCEPT:
                self.writer.get_buffer().begin_user_action()
                self.insert_at_cursor('\n' + tde.get_table())
                self.writer.get_buffer().end_user_action()
                self.do_it()
            tde.destroy()
            self.writer.grab_focus()
        elif option == 'insert-date':
            self.writer.get_buffer().begin_user_action()
            self.insert_at_cursor(
                datetime.datetime.fromtimestamp(
                    time.time()).strftime('%A, %d de %B de %Y'))
            self.writer.grab_focus()
            self.do_it()
        elif option == 'preview':
            if self.preview_or_html.get_label() == _('Html'):
                self.preview_or_html.set_label(_('Html'))
                self.show_source_code(False)
            else:
                self.preview_or_html.set_label(_('Preview'))
                self.show_source_code(True)
        elif option == 'spellcheck':
            if self.tools['spellcheck'].get_active():
                self.spellchecker.attach(self.writer)
            else:
                self.spellchecker.detach()

    def get_first_n_characters_at_previous_line(self, n):
        textbuffer = self.writer.get_buffer()
        cursor_mark = textbuffer.get_insert()
        iterator = textbuffer.get_iter_at_mark(cursor_mark)
        if iterator.get_line() > 0:
            iterator.backward_line()
        else:
            if not iterator.is_start():
                iterator.backward_chars(iterator.get_line_offset())
        left_mark = textbuffer.create_mark('left_mark', iterator, False)
        iterator.forward_chars(n)
        right_mark = textbuffer.create_mark('right_mark', iterator, False)
        iterator_left = textbuffer.get_iter_at_mark(left_mark)
        iterator_right = textbuffer.get_iter_at_mark(right_mark)
        textbuffer.delete_mark_by_name('left_mark')
        textbuffer.delete_mark_by_name('right_mark')
        thetext = textbuffer.get_text(iterator_left, iterator_right, True)
        return thetext

    def insert_at_start_of_line(self, tag):
        textbuffer = self.writer.get_buffer()
        cursor_mark = textbuffer.get_insert()
        iterator_cursor = textbuffer.get_iter_at_mark(cursor_mark)
        iteratwordstart = textbuffer.get_iter_at_mark(cursor_mark)
        iteratwordstart.backward_chars(1)
        left_mark = textbuffer.create_mark('left', iteratwordstart, False)
        iterator_left = textbuffer.get_iter_at_mark(left_mark)
        temporal = textbuffer.get_text(iterator_left, iterator_cursor, True)
        textbuffer.delete_mark_by_name('left')
        if temporal.find('\r') > -1 or temporal.find('\n') > -1 or\
                iterator_cursor.is_start():
            textbuffer.insert_at_cursor('%s ' % tag)
        else:
            textbuffer.insert_at_cursor('\n%s ' % tag)

    def insert_at_cursor(self, tag):
        textbuffer = self.writer.get_buffer()
        textbuffer.insert_at_cursor('%s' % tag)

    def wrap_text(self, start_tag, end_tag):
        textbuffer = self.writer.get_buffer()
        cursor_mark = textbuffer.get_insert()
        bounds = textbuffer.get_selection_bounds()
        if (bounds):
            iteratwordstart, iteratwordend = bounds
        else:
            iteratwordstart = textbuffer.get_iter_at_mark(cursor_mark)
            iteratwordstart.backward_chars(1)
            left = textbuffer.create_mark('left', iteratwordstart, False)
            iteratwordstart.forward_chars(2)
            right = textbuffer.create_mark('right', iteratwordstart, False)
            iterator_left = textbuffer.get_iter_at_mark(left)
            iterator_right = textbuffer.get_iter_at_mark(right)
            temporal = textbuffer.get_text(iterator_left, iterator_right, True)
            textbuffer.delete_mark_by_name('left')
            textbuffer.delete_mark_by_name('right')
            if temporal.find('\r') > -1 or temporal.find('\n') > -1 or\
                    temporal.find(' ') > -1 or temporal.find('\'') > -1 or\
                    temporal.find('\"') > -1:
                iteratwordstart = textbuffer.get_iter_at_mark(cursor_mark)
                iteratwordend = textbuffer.get_iter_at_mark(cursor_mark)
            else:
                iteratwordstart = textbuffer.get_iter_at_mark(cursor_mark)
                if not iteratwordstart.starts_word():
                    iteratwordstart.backward_word_start()
                iteratwordend = textbuffer.get_iter_at_mark(cursor_mark)
                if not iteratwordend.ends_word():
                    iteratwordend.forward_word_end()
        thetext = textbuffer.get_text(iteratwordstart, iteratwordend, True)
        textbuffer.delete(iteratwordstart, iteratwordend)
        textbuffer.insert_at_cursor(start_tag+thetext+end_tag)

    def wrap_selection(self, start_tag, end_tag):
        """This fucntion is used to wrap the currently selected
        text in the gtk.TextView with start_tag and end_tag. If
        there is no selection start_tag and end_tag will be
        inserted at the cursor position
        start_tag - The text that will go at the start of the
        selection.
        end_tag - The text that will go at the end of the
        selection."""
        textbuffer = self.writer.get_buffer()
        start, end = self.get_selection_iters()
        if ((not start)or(not end)):
            self.show_error_dlg("Error inserting text")
            return
        # Create a mark at the start and end
        start_mark = textbuffer.create_mark(None, start, True)
        end_mark = textbuffer.create_mark(None, end, False)
        # Insert the start_tag
        textbuffer.insert(start, start_tag)
        # Get the end iter again
        end = textbuffer.get_iter_at_mark(end_mark)
        # Insert the end tag
        textbuffer.insert(end, end_tag)
        # Get the start and end iters
        start = textbuffer.get_iter_at_mark(start_mark)
        end = textbuffer.get_iter_at_mark(end_mark)
        # Select the text
        textbuffer.select_range(end, start)
        # Delete the gtk.TextMark objects
        textbuffer.delete_mark(start_mark)
        textbuffer.delete_mark(end_mark)

    def remove_all_tag(self, tag_name):
        start_iter = self.writer.get_buffer().get_start_iter()
        end_iter = self.writer.get_buffer().get_end_iter()
        self.writer.get_buffer().remove_tag_by_name(
            tag_name, start_iter, end_iter)

    def search_and_mark(self, text, start):
        end = self.writer.get_buffer().get_end_iter()
        match = start.forward_search(text, 0, end)
        if match is not None:
            match_start, match_end = match
            self.writer.get_buffer().apply_tag(
                self.tag_found, match_start, match_end)
            self.search_and_mark(text, match_end)

    def search_and_replace(self, text_to_search, text_replace_with, start):
        end = self.writer.get_buffer().get_end_iter()
        match = start.forward_search(text_to_search, 0, end)
        if match is not None:
            match_start, match_end = match
            self.writer.get_buffer().delete(match_start, match_end)
            self.writer.get_buffer().insert(match_start, text_replace_with)
            iterator_cursor = self.writer.get_buffer().get_iter_at_mark(
                self.writer.get_buffer().get_insert())
            self.search_and_replace(
                text_to_search, text_replace_with, iterator_cursor)


def main():
    app = MainApplication()
    app.run('')


if __name__ == "__main__":
    main()
    '''
    # Use threads
    GObject.threads_init()
    win = uText()
    # win.connect("delete-event", Gtk.main_quit)
    Gtk.main()
    sys.exit(Gtk.main_quit())
    '''
