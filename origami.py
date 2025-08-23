#!/usr/bin/env python3
"""
Origami Store - A GTK3 frontend for Flathub
A complete store application for browsing, installing, and managing Flatpak applications
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf, Gdk, GLib, Gio
import subprocess
import json
import threading
import requests
import os
import tempfile
from urllib.parse import urlparse
import time
from io import BytesIO
import hashlib

class FlatpakStore:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.installed_apps = set()
        self.available_apps = []
        self.current_operations = {}
        self.image_cache = {}
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "origami-store")
        self.dark_mode = self.detect_dark_mode()
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.setup_ui()
        self.load_installed_apps()
        
    def detect_dark_mode(self):
        """Detect if system is using dark mode"""
        try:
            # Try to get GTK theme
            settings = Gtk.Settings.get_default()
            theme_name = settings.get_property("gtk-theme-name").lower()
            if "dark" in theme_name:
                return True
            
            # Check if prefer-dark-theme is set
            if settings.get_property("gtk-application-prefer-dark-theme"):
                return True
                
            # Check environment variable
            if os.environ.get("GTK_THEME", "").lower().endswith("dark"):
                return True
                
        except:
            pass
        
        return False
    
    def setup_ui(self):
        """Setup the main UI"""
        # Main window
        self.window = Gtk.Window()
        self.window.set_title("Origami Store")
        self.window.set_default_size(1200, 800)
        self.window.set_icon_name("application-x-appliance")
        self.window.connect("destroy", Gtk.main_quit)
        
        # Apply modern styling with dark mode support
        css_provider = Gtk.CssProvider()
        
        # Base colors for light/dark mode
        if self.dark_mode:
            css_data = b"""
            window {
                background: #2b2b2b;
                color: #ffffff;
            }
            
            .header-bar {
                background: linear-gradient(to bottom, #404040, #2b2b2b);
                color: #ffffff;
                border-bottom: 1px solid #555555;
            }
            
            .app-card {
                background: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 12px;
                margin: 8px;
                padding: 0;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }
            
            .app-card:hover {
                box-shadow: 0 8px 16px rgba(0,0,0,0.4);
                border-color: #4a90e2;
            }
            
            .app-banner {
                background: #2b2b2b;
                border-radius: 12px 12px 0 0;
                min-height: 120px;
            }
            
            .app-content {
                padding: 16px;
                background: #3c3c3c;
                border-radius: 0 0 12px 12px;
            }
            
            .app-title {
                font-weight: bold;
                font-size: 18px;
                color: #ffffff;
                margin-bottom: 4px;
            }
            
            .app-id {
                color: #888888;
                font-size: 12px;
                margin-bottom: 8px;
            }
            
            .app-description {
                color: #cccccc;
                font-size: 14px;
            }
            
            .install-button {
                background: linear-gradient(to bottom, #27ae60, #229954);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            
            .install-button:hover {
                background: linear-gradient(to bottom, #229954, #1e8449);
                box-shadow: 0 4px 8px rgba(39, 174, 96, 0.3);
            }
            
            .uninstall-button {
                background: linear-gradient(to bottom, #e74c3c, #c0392b);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            
            .uninstall-button:hover {
                background: linear-gradient(to bottom, #c0392b, #a93226);
                box-shadow: 0 4px 8px rgba(231, 76, 60, 0.3);
            }
            
            .category-button {
                background: #555555;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 8px;
                margin: 4px;
                padding: 10px 16px;
            }
            
            .category-button:checked {
                background: linear-gradient(to bottom, #4a90e2, #357abd);
                color: white;
                border-color: #357abd;
                box-shadow: 0 2px 4px rgba(74, 144, 226, 0.3);
            }
            
            .search-entry {
                border-radius: 20px;
                padding: 12px 20px;
                border: 2px solid #555555;
                background: #3c3c3c;
                color: #ffffff;
            }
            
            .search-entry:focus {
                border-color: #4a90e2;
                box-shadow: 0 0 8px rgba(74, 144, 226, 0.3);
            }
            
            .progress-bar {
                border-radius: 4px;
                background: #555555;
            }
            
            .progress-bar progress {
                background: linear-gradient(to right, #4a90e2, #357abd);
            }
            
            scrolledwindow {
                background: #2b2b2b;
            }
            
            notebook {
                background: #2b2b2b;
            }
            
            notebook header {
                background: #3c3c3c;
                border-bottom: 1px solid #555555;
            }
            
            notebook tab {
                background: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 12px 24px;
            }
            
            notebook tab:checked {
                background: #4a90e2;
                color: white;
            }
            
            statusbar {
                background: #3c3c3c;
                color: #ffffff;
                border-top: 1px solid #555555;
                padding: 8px;
            }
            """
        else:
            css_data = b"""
            window {
                background: #f8f9fa;
                color: #2c3e50;
            }
            
            .header-bar {
                background: linear-gradient(to bottom, #4a90e2, #357abd);
                color: white;
                border-bottom: 1px solid #357abd;
            }
            
            .app-card {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin: 8px;
                padding: 0;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            
            .app-card:hover {
                box-shadow: 0 8px 16px rgba(0,0,0,0.15);
                border-color: #4a90e2;
            }
            
            .app-banner {
                background: #f8f9fa;
                border-radius: 12px 12px 0 0;
                min-height: 120px;
            }
            
            .app-content {
                padding: 16px;
                background: white;
                border-radius: 0 0 12px 12px;
            }
            
            .app-title {
                font-weight: bold;
                font-size: 18px;
                color: #2c3e50;
                margin-bottom: 4px;
            }
            
            .app-id {
                color: #7f8c8d;
                font-size: 12px;
                margin-bottom: 8px;
            }
            
            .app-description {
                color: #5a6c7d;
                font-size: 14px;
            }
            
            .install-button {
                background: linear-gradient(to bottom, #27ae60, #229954);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            
            .install-button:hover {
                background: linear-gradient(to bottom, #229954, #1e8449);
                box-shadow: 0 4px 8px rgba(39, 174, 96, 0.3);
            }
            
            .uninstall-button {
                background: linear-gradient(to bottom, #e74c3c, #c0392b);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            
            .uninstall-button:hover {
                background: linear-gradient(to bottom, #c0392b, #a93226);
                box-shadow: 0 4px 8px rgba(231, 76, 60, 0.3);
            }
            
            .category-button {
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                margin: 4px;
                padding: 10px 16px;
            }
            
            .category-button:checked {
                background: linear-gradient(to bottom, #4a90e2, #357abd);
                color: white;
                border-color: #357abd;
                box-shadow: 0 2px 4px rgba(74, 144, 226, 0.3);
            }
            
            .search-entry {
                border-radius: 20px;
                padding: 12px 20px;
                border: 2px solid #bdc3c7;
                background: white;
            }
            
            .search-entry:focus {
                border-color: #4a90e2;
                box-shadow: 0 0 8px rgba(74, 144, 226, 0.3);
            }
            
            .progress-bar {
                border-radius: 4px;
            }
            """
        
        css_provider.load_from_data(css_data)
        
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Origami Store")
        header.set_subtitle("Browse and install applications from Flathub")
        header.get_style_context().add_class("header-bar")
        
        # Dark mode toggle button
        self.dark_mode_btn = Gtk.ToggleButton()
        self.dark_mode_btn.set_active(self.dark_mode)
        dark_icon = "weather-clear-night-symbolic" if self.dark_mode else "weather-clear-symbolic"
        dark_image = Gtk.Image.new_from_icon_name(dark_icon, Gtk.IconSize.BUTTON)
        self.dark_mode_btn.add(dark_image)
        self.dark_mode_btn.set_tooltip_text("Toggle dark mode")
        self.dark_mode_btn.connect("toggled", self.toggle_dark_mode)
        header.pack_start(self.dark_mode_btn)
        
        # Search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search applications...")
        self.search_entry.set_size_request(300, -1)
        self.search_entry.get_style_context().add_class("search-entry")
        self.search_entry.connect("search-changed", self.on_search_changed)
        header.pack_end(self.search_entry)
        
        # Refresh button
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_btn.set_tooltip_text("Refresh app list")
        refresh_btn.connect("clicked", self.refresh_apps)
        header.pack_end(refresh_btn)
        
        self.window.set_titlebar(header)
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(main_box)
        
        # Notebook for different views
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(True)
        main_box.pack_start(self.notebook, True, True, 0)
        
        # Store tab
        self.setup_store_tab()
        
        # Installed apps tab
        self.setup_installed_tab()
        
        # Status bar
        self.status_bar = Gtk.Statusbar()
        self.status_context_id = self.status_bar.get_context_id("main")
        main_box.pack_end(self.status_bar, False, False, 0)
        
        # Progress bar (hidden by default)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_no_show_all(True)
        self.progress_bar.get_style_context().add_class("progress-bar")
        main_box.pack_end(self.progress_bar, False, False, 0)
        
    def toggle_dark_mode(self, button):
        """Toggle between light and dark mode"""
        self.dark_mode = button.get_active()
        
        # Update button icon
        icon_name = "weather-clear-night-symbolic" if self.dark_mode else "weather-clear-symbolic"
        for child in button.get_children():
            button.remove(child)
        new_image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        button.add(new_image)
        button.show_all()
        
        # Reapply CSS
        self.setup_ui()
        self.refresh_current_view()
    
    def get_app_icon_url(self, app_id):
        """Get the URL for app icon from Flathub"""
        return f"https://flathub.org/repo/appstream/x86_64/icons/128x128/{app_id}.png"
    
    def get_app_screenshot_urls(self, app_id):
        """Get screenshot URLs for an app"""
        # Try to get screenshots from Flathub API
        try:
            response = requests.get(f"https://flathub.org/api/v1/apps/{app_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                screenshots = data.get('screenshots', [])
                if screenshots:
                    return [shot.get('imgDesktopUrl', '') for shot in screenshots[:1]]  # Take first screenshot
        except:
            pass
        
        # Fallback to icon
        return [self.get_app_icon_url(app_id)]
    
    def download_image(self, url, max_size=(400, 200)):
        """Download and cache an image"""
        if not url:
            return None
            
        # Create cache key
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.png")
        
        # Check if cached
        if os.path.exists(cache_path):
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(cache_path, max_size[0], max_size[1], True)
            except:
                os.remove(cache_path)  # Remove corrupted cache
        
        try:
            response = requests.get(url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Load and return pixbuf
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(cache_path, max_size[0], max_size[1], True)
            
        except Exception as e:
            print(f"Error downloading image {url}: {e}")
            return None
    
    def load_app_media_async(self, app_id, image_widget, screenshot=True):
        """Load app icon or screenshot asynchronously"""
        def load_worker():
            try:
                if screenshot:
                    urls = self.get_app_screenshot_urls(app_id)
                    pixbuf = None
                    for url in urls:
                        pixbuf = self.download_image(url, (400, 180))
                        if pixbuf:
                            break
                    
                    if not pixbuf:  # Fallback to icon
                        icon_url = self.get_app_icon_url(app_id)
                        pixbuf = self.download_image(icon_url, (128, 128))
                else:
                    icon_url = self.get_app_icon_url(app_id)
                    pixbuf = self.download_image(icon_url, (64, 64))
                
                if pixbuf:
                    GLib.idle_add(lambda: image_widget.set_from_pixbuf(pixbuf) if not image_widget.get_parent() is None else None)
                    
            except Exception as e:
                print(f"Error loading media for {app_id}: {e}")
        
        threading.Thread(target=load_worker, daemon=True).start()
        
    def setup_store_tab(self):
        """Setup the store browsing tab"""
        store_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        store_box.set_margin_left(20)
        store_box.set_margin_right(20)
        store_box.set_margin_top(20)
        store_box.set_margin_bottom(20)
        
        # Categories
        categories_frame = Gtk.Frame()
        categories_frame.set_label("Categories")
        categories_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        categories_box.set_margin_left(10)
        categories_box.set_margin_right(10)
        categories_box.set_margin_top(10)
        categories_box.set_margin_bottom(10)
        
        self.category_buttons = {}
        categories = [
            ("All", "all"),
            ("Audio & Video", "AudioVideo"),
            ("Development", "Development"),
            ("Education", "Education"),
            ("Games", "Game"),
            ("Graphics", "Graphics"),
            ("Internet", "Network"),
            ("Office", "Office"),
            ("System", "System"),
            ("Utilities", "Utility")
        ]
        
        for label, category in categories:
            btn = Gtk.ToggleButton(label=label)
            btn.get_style_context().add_class("category-button")
            btn.connect("toggled", self.on_category_changed, category)
            self.category_buttons[category] = btn
            categories_box.pack_start(btn, False, False, 0)
        
        # Set "All" as default
        self.category_buttons["all"].set_active(True)
        self.current_category = "all"
        
        categories_frame.add(categories_box)
        store_box.pack_start(categories_frame, False, False, 0)
        
        # Scrolled window for apps
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        # Apps container
        self.apps_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scrolled.add(self.apps_container)
        store_box.pack_start(scrolled, True, True, 0)
        
        # Loading spinner
        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_size_request(50, 50)
        self.loading_spinner.set_no_show_all(True)
        store_box.pack_start(self.loading_spinner, False, False, 20)
        
        self.notebook.append_page(store_box, Gtk.Label(label="Store"))
        
        # Load apps in background
        threading.Thread(target=self.load_flathub_apps, daemon=True).start()
        
    def setup_installed_tab(self):
        """Setup the installed apps tab"""
        installed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        installed_box.set_margin_left(20)
        installed_box.set_margin_right(20)
        installed_box.set_margin_top(20)
        installed_box.set_margin_bottom(20)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_label = Gtk.Label()
        title_label.set_markup("<big><b>Installed Applications</b></big>")
        title_label.set_halign(Gtk.Align.START)
        header_box.pack_start(title_label, True, True, 0)
        
        update_all_btn = Gtk.Button(label="Update All")
        update_all_btn.get_style_context().add_class("install-button")
        update_all_btn.connect("clicked", self.update_all_apps)
        header_box.pack_end(update_all_btn, False, False, 0)
        
        installed_box.pack_start(header_box, False, False, 0)
        
        # Scrolled window for installed apps
        scrolled_installed = Gtk.ScrolledWindow()
        scrolled_installed.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.installed_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scrolled_installed.add(self.installed_container)
        installed_box.pack_start(scrolled_installed, True, True, 0)
        
        self.notebook.append_page(installed_box, Gtk.Label(label="Installed"))
        
    def load_installed_apps(self):
        """Load currently installed Flatpak applications"""
        try:
            result = subprocess.run(['flatpak', 'list', '--app', '--columns=application,name,description'], 
                                  capture_output=True, text=True, check=True)
            
            self.installed_apps.clear()
            GLib.idle_add(self.clear_installed_container)
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        app_id = parts[0]
                        name = parts[1] if len(parts) > 1 else app_id
                        description = parts[2] if len(parts) > 2 else "No description available"
                        
                        self.installed_apps.add(app_id)
                        GLib.idle_add(self.add_installed_app_card, app_id, name, description)
                        
        except subprocess.CalledProcessError as e:
            GLib.idle_add(self.show_status, f"Error loading installed apps: {e}")
        except Exception as e:
            GLib.idle_add(self.show_status, f"Error: {e}")
    
    def clear_installed_container(self):
        """Clear the installed apps container"""
        for child in self.installed_container.get_children():
            child.destroy()
    
    def add_installed_app_card(self, app_id, name, description):
        """Add an installed app card to the UI with enhanced styling"""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.get_style_context().add_class("app-card")
        card.set_margin_left(10)
        card.set_margin_right(10)
        
        # Header with icon
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        header_box.get_style_context().add_class("app-content")
        header_box.set_margin_top(8)
        header_box.set_margin_bottom(8)
        
        # App icon
        app_icon = Gtk.Image()
        app_icon.set_size_request(64, 64)
        self.load_app_media_async(app_id, app_icon, screenshot=False)
        header_box.pack_start(app_icon, False, False, 0)
        
        # App info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        info_box.set_halign(Gtk.Align.START)
        
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{name}</b>")
        title_label.get_style_context().add_class("app-title")
        title_label.set_halign(Gtk.Align.START)
        info_box.pack_start(title_label, False, False, 0)
        
        id_label = Gtk.Label(label=app_id)
        id_label.set_halign(Gtk.Align.START)
        id_label.get_style_context().add_class("app-id")
        info_box.pack_start(id_label, False, False, 0)
        
        desc_label = Gtk.Label(label=description[:100] + "..." if len(description) > 100 else description)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.get_style_context().add_class("app-description")
        desc_label.set_line_wrap(True)
        info_box.pack_start(desc_label, False, False, 0)
        
        header_box.pack_start(info_box, True, True, 0)
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        run_btn = Gtk.Button(label="Run")
        run_btn.connect("clicked", self.run_app, app_id)
        button_box.pack_start(run_btn, False, False, 0)
        
        update_btn = Gtk.Button(label="Update")
        update_btn.get_style_context().add_class("install-button")
        update_btn.connect("clicked", self.update_app, app_id, name)
        button_box.pack_start(update_btn, False, False, 0)
        
        uninstall_btn = Gtk.Button(label="Uninstall")
        uninstall_btn.get_style_context().add_class("uninstall-button")
        uninstall_btn.connect("clicked", self.uninstall_app, app_id, name)
        button_box.pack_start(uninstall_btn, False, False, 0)
        
        header_box.pack_end(button_box, False, False, 0)
        
        card.pack_start(header_box, False, False, 0)
        
        self.installed_container.pack_start(card, False, False, 0)
        card.show_all()
    
    def load_flathub_apps(self):
        """Load applications from Flathub API or fallback to local flatpak search"""
        try:
            GLib.idle_add(self.show_loading, True)
            GLib.idle_add(self.show_status, "Loading applications from Flathub...")
            
            # Try the new Flathub API v2 endpoint first
            try:
                response = requests.get("https://flathub.org/api/v2/apps", timeout=30)
                response.raise_for_status()
                self.available_apps = self._parse_v2_response(response.json())
                GLib.idle_add(self.show_status, f"Loaded {len(self.available_apps)} applications from API")
            except:
                # Fallback to using flatpak search for available apps
                GLib.idle_add(self.show_status, "API unavailable, using local flatpak search...")
                self.available_apps = self._load_apps_via_flatpak()
                GLib.idle_add(self.show_status, f"Loaded {len(self.available_apps)} applications via flatpak search")
            
            GLib.idle_add(self.show_loading, False)
            GLib.idle_add(self.display_apps)
            
        except Exception as e:
            GLib.idle_add(self.show_loading, False)
            GLib.idle_add(self.show_status, f"Error: {e}")
    
    def _parse_v2_response(self, data):
        """Parse Flathub API v2 response format"""
        apps = []
        if isinstance(data, list):
            for app in data:
                apps.append({
                    'flatpakAppId': app.get('id', app.get('flatpakAppId', '')),
                    'name': app.get('name', app.get('id', '')),
                    'summary': app.get('summary', app.get('description', 'No description available')),
                    'categories': app.get('categories', []),
                    'icon': app.get('icon', ''),
                    'screenshots': app.get('screenshots', [])
                })
        elif isinstance(data, dict) and 'apps' in data:
            for app in data['apps']:
                apps.append({
                    'flatpakAppId': app.get('id', app.get('flatpakAppId', '')),
                    'name': app.get('name', app.get('id', '')),
                    'summary': app.get('summary', app.get('description', 'No description available')),
                    'categories': app.get('categories', []),
                    'icon': app.get('icon', ''),
                    'screenshots': app.get('screenshots', [])
                })
        return apps
    
    def _load_apps_via_flatpak(self):
        """Fallback method: Load apps using flatpak search command"""
        apps = []
        try:
            # Get list of available apps from flathub remote
            result = subprocess.run([
                'flatpak', 'remote-ls', '--app', 'flathub', '--columns=application,name,description'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            app_id = parts[0]
                            name = parts[1] if parts[1] else app_id
                            description = parts[2] if len(parts) > 2 else "No description available"
                            
                            # Try to determine category from app ID
                            categories = self._guess_category_from_id(app_id)
                            
                            apps.append({
                                'flatpakAppId': app_id,
                                'name': name,
                                'summary': description,
                                'categories': categories
                            })
            
            # If that fails, try a broader approach
            if not apps:
                # Get some popular known apps as a fallback
                popular_apps = [
                    ('org.mozilla.firefox', 'Firefox', 'Web browser', ['Network']),
                    ('org.libreoffice.LibreOffice', 'LibreOffice', 'Office suite', ['Office']),
                    ('org.gimp.GIMP', 'GIMP', 'Image editor', ['Graphics']),
                    ('org.videolan.VLC', 'VLC', 'Media player', ['AudioVideo']),
                    ('org.blender.Blender', 'Blender', '3D creation suite', ['Graphics']),
                    ('com.valvesoftware.Steam', 'Steam', 'Gaming platform', ['Game']),
                    ('org.telegram.desktop', 'Telegram', 'Messaging app', ['Network']),
                    ('com.spotify.Client', 'Spotify', 'Music streaming', ['AudioVideo']),
                    ('org.gnome.gedit', 'Text Editor', 'Simple text editor', ['Utility']),
                    ('org.kde.kate', 'Kate', 'Advanced text editor', ['Development'])
                ]
                
                for app_id, name, summary, categories in popular_apps:
                    apps.append({
                        'flatpakAppId': app_id,
                        'name': name,
                        'summary': summary,
                        'categories': categories
                    })
                    
        except Exception as e:
            print(f"Error in fallback app loading: {e}")
            
        return apps
    
    def _guess_category_from_id(self, app_id):
        """Guess app category from its ID"""
        app_id_lower = app_id.lower()
        
        if any(term in app_id_lower for term in ['firefox', 'chrome', 'telegram', 'discord', 'thunderbird']):
            return ['Network']
        elif any(term in app_id_lower for term in ['libreoffice', 'writer', 'calc']):
            return ['Office']
        elif any(term in app_id_lower for term in ['gimp', 'inkscape', 'blender', 'krita']):
            return ['Graphics']
        elif any(term in app_id_lower for term in ['vlc', 'audacity', 'spotify']):
            return ['AudioVideo']
        elif any(term in app_id_lower for term in ['steam', 'game', 'chess', 'puzzle']):
            return ['Game']
        elif any(term in app_id_lower for term in ['code', 'atom', 'eclipse', 'git']):
            return ['Development']
        elif any(term in app_id_lower for term in ['calculator', 'archive', 'file']):
            return ['Utility']
        else:
            return ['Other']
    
    def show_loading(self, show):
        """Show or hide loading spinner"""
        if show:
            self.loading_spinner.show()
            self.loading_spinner.start()
        else:
            self.loading_spinner.stop()
            self.loading_spinner.hide()
    
    def display_apps(self, search_term=""):
        """Display apps in the store tab"""
        # Clear existing apps
        for child in self.apps_container.get_children():
            child.destroy()
        
        filtered_apps = self.filter_apps(search_term)
        
        if not filtered_apps:
            no_apps_label = Gtk.Label()
            no_apps_label.set_markup("<big>No applications found</big>")
            no_apps_label.get_style_context().add_class("app-description")
            self.apps_container.pack_start(no_apps_label, False, False, 20)
            no_apps_label.show()
            return
        
        # Display apps (limit to 50 for performance)
        for app in filtered_apps[:50]:
            self.add_app_card(app)
        
        if len(filtered_apps) > 50:
            more_label = Gtk.Label()
            more_label.set_markup(f"<i>... and {len(filtered_apps) - 50} more. Use search to narrow results.</i>")
            more_label.get_style_context().add_class("app-description")
            self.apps_container.pack_start(more_label, False, False, 10)
            more_label.show()
    
    def filter_apps(self, search_term=""):
        """Filter apps based on category and search term"""
        filtered = []
        
        for app in self.available_apps:
            # Category filter
            if self.current_category != "all":
                app_categories = app.get("categories", [])
                if self.current_category not in app_categories:
                    continue
            
            # Search filter
            if search_term:
                search_lower = search_term.lower()
                name = app.get("name", "").lower()
                summary = app.get("summary", "").lower()
                app_id = app.get("flatpakAppId", "").lower()
                
                if not (search_lower in name or search_lower in summary or search_lower in app_id):
                    continue
            
            filtered.append(app)
        
        return filtered
    
    def add_app_card(self, app):
        """Add an app card to the store with banner image and icon"""
        app_id = app.get("flatpakAppId", "")
        name = app.get("name", app_id)
        summary = app.get("summary", "No description available")
        
        # Main card container
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.get_style_context().add_class("app-card")
        card.set_margin_left(10)
        card.set_margin_right(10)
        
        # Banner/Screenshot area
        banner_overlay = Gtk.Overlay()
        banner_overlay.get_style_context().add_class("app-banner")
        banner_overlay.set_size_request(400, 120)
        
        # Banner image (screenshot or large icon)
        banner_image = Gtk.Image()
        banner_image.set_size_request(400, 120)
        banner_overlay.add(banner_image)
        
        # App icon overlay (bottom left of banner)
        icon_box = Gtk.Box()
        icon_box.set_halign(Gtk.Align.START)
        icon_box.set_valign(Gtk.Align.END)
        icon_box.set_margin_left(16)
        icon_box.set_margin_bottom(8)
        
        app_icon = Gtk.Image()
        app_icon.set_size_request(48, 48)
        
        # Create a frame for the icon with rounded corners
        icon_frame = Gtk.Frame()
        icon_frame.set_shadow_type(Gtk.ShadowType.OUT)
        icon_frame.add(app_icon)
        icon_box.pack_start(icon_frame, False, False, 0)
        
        banner_overlay.add_overlay(icon_box)
        card.pack_start(banner_overlay, False, False, 0)
        
        # Content area
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        content_box.get_style_context().add_class("app-content")
        
        # App info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_halign(Gtk.Align.START)
        info_box.set_margin_left(8)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{name}</b>")
        title_label.get_style_context().add_class("app-title")
        title_label.set_halign(Gtk.Align.START)
        info_box.pack_start(title_label, False, False, 0)
        
        # App ID
        id_label = Gtk.Label(label=app_id)
        id_label.set_halign(Gtk.Align.START)
        id_label.get_style_context().add_class("app-id")
        info_box.pack_start(id_label, False, False, 0)
        
        # Description
        desc_label = Gtk.Label(label=summary[:120] + "..." if len(summary) > 120 else summary)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.get_style_context().add_class("app-description")
        desc_label.set_line_wrap(True)
        desc_label.set_max_width_chars(50)
        info_box.pack_start(desc_label, False, False, 0)
        
        content_box.pack_start(info_box, True, True, 0)
        
        # Action buttons area
        is_installed = app_id in self.installed_apps
        
        if app_id in self.current_operations:
            # Show progress
            progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            progress_label = Gtk.Label(label=self.current_operations[app_id])
            progress_bar = Gtk.ProgressBar()
            progress_bar.pulse()
            GLib.timeout_add(100, lambda: progress_bar.pulse() or True)
            progress_box.pack_start(progress_label, False, False, 0)
            progress_box.pack_start(progress_bar, False, False, 0)
            content_box.pack_end(progress_box, False, False, 0)
        else:
            button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            button_box.set_margin_right(8)
            
            if is_installed:
                uninstall_btn = Gtk.Button(label="Uninstall")
                uninstall_btn.get_style_context().add_class("uninstall-button")
                uninstall_btn.connect("clicked", self.uninstall_app, app_id, name)
                button_box.pack_start(uninstall_btn, False, False, 0)
                
                run_btn = Gtk.Button(label="Run")
                run_btn.connect("clicked", self.run_app, app_id)
                button_box.pack_start(run_btn, False, False, 0)
            else:
                install_btn = Gtk.Button(label="Install")
                install_btn.get_style_context().add_class("install-button")
                install_btn.connect("clicked", self.install_app, app_id, name)
                button_box.pack_start(install_btn, False, False, 0)
            
            content_box.pack_end(button_box, False, False, 0)
        
        card.pack_start(content_box, False, False, 0)
        
        # Load images asynchronously
        self.load_app_media_async(app_id, banner_image, screenshot=True)
        self.load_app_media_async(app_id, app_icon, screenshot=False)
        
        self.apps_container.pack_start(card, False, False, 0)
        card.show_all()
    
    def install_app(self, button, app_id, name):
        """Install a Flatpak application"""
        self.current_operations[app_id] = f"Installing {name}..."
        self.refresh_current_view()
        
        def install_worker():
            try:
                self.show_progress(True)
                GLib.idle_add(self.show_status, f"Installing {name}...")
                
                process = subprocess.Popen(
                    ['flatpak', 'install', '--user', '-y', 'flathub', app_id],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # Read output line by line
                for line in iter(process.stdout.readline, ''):
                    if line.strip():
                        GLib.idle_add(self.show_status, f"Installing {name}: {line.strip()}")
                
                process.wait()
                
                if process.returncode == 0:
                    self.installed_apps.add(app_id)
                    GLib.idle_add(self.show_status, f"Successfully installed {name}")
                    GLib.idle_add(self.load_installed_apps)
                else:
                    GLib.idle_add(self.show_status, f"Failed to install {name}")
                
            except Exception as e:
                GLib.idle_add(self.show_status, f"Error installing {name}: {e}")
            finally:
                if app_id in self.current_operations:
                    del self.current_operations[app_id]
                GLib.idle_add(self.refresh_current_view)
                GLib.idle_add(self.show_progress, False)
        
        threading.Thread(target=install_worker, daemon=True).start()
    
    def uninstall_app(self, button, app_id, name):
        """Uninstall a Flatpak application"""
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Uninstall {name}?"
        )
        dialog.format_secondary_text(f"This will remove {name} ({app_id}) from your system.")
        
        response = dialog.run()
        dialog.destroy()
        
        if response != Gtk.ResponseType.YES:
            return
        
        self.current_operations[app_id] = f"Uninstalling {name}..."
        self.refresh_current_view()
        
        def uninstall_worker():
            try:
                self.show_progress(True)
                GLib.idle_add(self.show_status, f"Uninstalling {name}...")
                
                result = subprocess.run(
                    ['flatpak', 'uninstall', '--user', '-y', app_id],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.installed_apps.discard(app_id)
                    GLib.idle_add(self.show_status, f"Successfully uninstalled {name}")
                    GLib.idle_add(self.load_installed_apps)
                else:
                    GLib.idle_add(self.show_status, f"Failed to uninstall {name}: {result.stderr}")
                
            except Exception as e:
                GLib.idle_add(self.show_status, f"Error uninstalling {name}: {e}")
            finally:
                if app_id in self.current_operations:
                    del self.current_operations[app_id]
                GLib.idle_add(self.refresh_current_view)
                GLib.idle_add(self.show_progress, False)
        
        threading.Thread(target=uninstall_worker, daemon=True).start()
    
    def update_app(self, button, app_id, name):
        """Update a specific Flatpak application"""
        self.current_operations[app_id] = f"Updating {name}..."
        
        def update_worker():
            try:
                GLib.idle_add(self.show_status, f"Updating {name}...")
                
                result = subprocess.run(
                    ['flatpak', 'update', '--user', '-y', app_id],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    GLib.idle_add(self.show_status, f"Successfully updated {name}")
                else:
                    GLib.idle_add(self.show_status, f"No updates available for {name}")
                
            except Exception as e:
                GLib.idle_add(self.show_status, f"Error updating {name}: {e}")
            finally:
                if app_id in self.current_operations:
                    del self.current_operations[app_id]
                GLib.idle_add(self.load_installed_apps)
        
        threading.Thread(target=update_worker, daemon=True).start()
    
    def update_all_apps(self, button):
        """Update all installed Flatpak applications"""
        def update_all_worker():
            try:
                GLib.idle_add(self.show_status, "Updating all applications...")
                GLib.idle_add(self.show_progress, True)
                
                result = subprocess.run(
                    ['flatpak', 'update', '--user', '-y'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    GLib.idle_add(self.show_status, "All applications updated successfully")
                else:
                    GLib.idle_add(self.show_status, "Update completed with some issues")
                
                GLib.idle_add(self.load_installed_apps)
                
            except Exception as e:
                GLib.idle_add(self.show_status, f"Error updating applications: {e}")
            finally:
                GLib.idle_add(self.show_progress, False)
        
        threading.Thread(target=update_all_worker, daemon=True).start()
    
    def run_app(self, button, app_id):
        """Run a Flatpak application"""
        try:
            subprocess.Popen(['flatpak', 'run', app_id])
            self.show_status(f"Launched {app_id}")
        except Exception as e:
            self.show_status(f"Error launching {app_id}: {e}")
    
    def on_search_changed(self, entry):
        """Handle search entry changes"""
        search_term = entry.get_text().strip()
        if hasattr(self, 'search_timeout'):
            GLib.source_remove(self.search_timeout)
        
        # Debounce search
        self.search_timeout = GLib.timeout_add(300, lambda: self.display_apps(search_term))
    
    def on_category_changed(self, button, category):
        """Handle category button changes"""
        if not button.get_active():
            return
        
        # Uncheck other category buttons
        for cat, btn in self.category_buttons.items():
            if cat != category and btn.get_active():
                btn.set_active(False)
        
        self.current_category = category
        search_term = self.search_entry.get_text().strip()
        self.display_apps(search_term)
    
    def refresh_apps(self, button=None):
        """Refresh the app list from Flathub"""
        threading.Thread(target=self.load_flathub_apps, daemon=True).start()
        threading.Thread(target=self.load_installed_apps, daemon=True).start()
    
    def refresh_current_view(self):
        """Refresh the current view"""
        current_page = self.notebook.get_current_page()
        if current_page == 0:  # Store tab
            search_term = self.search_entry.get_text().strip()
            self.display_apps(search_term)
        else:  # Installed tab
            self.load_installed_apps()
    
    def show_status(self, message):
        """Show a status message"""
        self.status_bar.remove_all(self.status_context_id)
        self.status_bar.push(self.status_context_id, message)
    
    def show_progress(self, show):
        """Show or hide the progress bar"""
        if show:
            self.progress_bar.show()
            self.progress_bar.pulse()
            GLib.timeout_add(100, self._pulse_progress)
        else:
            self.progress_bar.hide()
    
    def _pulse_progress(self):
        """Pulse the progress bar"""
        if self.progress_bar.get_visible():
            self.progress_bar.pulse()
            return True
        return False
    
    def run(self):
        """Run the application"""
        # Check if Flatpak is installed
        try:
            subprocess.run(['flatpak', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Flatpak not found"
            )
            dialog.format_secondary_text(
                "Flatpak is not installed on your system. Please install Flatpak first:\n"
                "Ubuntu/Debian: sudo apt install flatpak\n"
                "Fedora: sudo dnf install flatpak\n"
                "Arch: sudo pacman -S flatpak"
            )
            dialog.run()
            dialog.destroy()
            return
        
        # Check if Flathub repo is added
        try:
            result = subprocess.run(['flatpak', 'remotes'], capture_output=True, text=True, check=True)
            if 'flathub' not in result.stdout:
                dialog = Gtk.MessageDialog(
                    transient_for=None,
                    flags=0,
                    message_type=Gtk.MessageType.QUESTION,
                    buttons=Gtk.ButtonsType.YES_NO,
                    text="Flathub repository not found"
                )
                dialog.format_secondary_text(
                    "The Flathub repository is not configured. Would you like to add it now?\n"
                    "This will run: flatpak remote-add --if-not-exists --user flathub https://flathub.org/repo/flathub.flatpakrepo"
                )
                
                response = dialog.run()
                dialog.destroy()
                
                if response == Gtk.ResponseType.YES:
                    try:
                        subprocess.run([
                            'flatpak', 'remote-add', '--if-not-exists', '--user', 
                            'flathub', 'https://flathub.org/repo/flathub.flatpakrepo'
                        ], check=True)
                        
                        success_dialog = Gtk.MessageDialog(
                            transient_for=None,
                            flags=0,
                            message_type=Gtk.MessageType.INFO,
                            buttons=Gtk.ButtonsType.OK,
                            text="Flathub repository added successfully"
                        )
                        success_dialog.run()
                        success_dialog.destroy()
                    except subprocess.CalledProcessError as e:
                        error_dialog = Gtk.MessageDialog(
                            transient_for=None,
                            flags=0,
                            message_type=Gtk.MessageType.ERROR,
                            buttons=Gtk.ButtonsType.OK,
                            text=f"Failed to add Flathub repository: {e}"
                        )
                        error_dialog.run()
                        error_dialog.destroy()
                        return
                else:
                    return
        except subprocess.CalledProcessError:
            pass  # Continue anyway
        
        self.window.show_all()
        self.show_status("Welcome to Origami Store")
        Gtk.main()

def main():
    """Main entry point"""
    # Enable Qt6 compatibility by setting environment variables
    os.environ.setdefault('QT_QPA_PLATFORMTHEME', 'gtk3')
    os.environ.setdefault('QT_STYLE_OVERRIDE', 'gtk2')
    
    try:
        app = FlatpakStore()
        app.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        
        # Show error dialog if possible
        try:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Application Error"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
        except:
            pass

if __name__ == "__main__":
    main()
