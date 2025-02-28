import customtkinter as ctk
import speech_recognition as sr
from gtts import gTTS
from deep_translator import GoogleTranslator
import threading
import os
from playsound import playsound
import queue
import pyttsx3

# Define language codes here
LANGUAGE_CODES = {
    "English": "en",
    "Hindi": "hi",
    "Bengali": "bn",
    "Spanish": "es",
    "Chinese (Simplified)": "zh-CN",
    "Russian": "ru",
    "Japanese": "ja",
    "Korean": "ko",
    "German": "de",
    "French": "fr",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Gujarati": "gu",
    "Punjabi": "pa"
}

# Modern color scheme
COLORS = {
    "bg_primary": "#1E1E1E",      # Dark background
    "bg_secondary": "#2D2D2D",    # Slightly lighter background
    "accent": "#007AFF",          # Bright blue accent
    "text_primary": "#FFFFFF",    # White text
    "text_secondary": "#B3B3B3",  # Light gray text
    "success": "#34C759",         # Green for success states
    "error": "#FF3B30",          # Red for errors
    "button_hover": "#0051FF",    # Darker blue for button hover
    "input_bg": "#363636",      # Slightly lighter than bg_primary for input
    "mode_toggle": "#505050",    # Color for mode toggle button
    "voice_settings": "#404040",  # Color for voice settings panel
    "settings_bg": "#2A2A2A",     # Background for settings popup
    "overlay": "#000000",         # Semi-transparent overlay
    "settings_button": "#404040", # Settings button color
    "light_bg_primary": "#D1F8EF",    # Lightest turquoise
    "light_bg_secondary": "#A1E3F9",   # Light blue
    "light_text_primary": "#3674B5",   # Dark blue
    "light_text_secondary": "#578FCA", # Medium blue
    "light_frame": "#A1E3F9",          # Light blue for frames
    "light_accent": "#3674B5",         # Dark blue for accents
    "light_button": "#578FCA",         # Medium blue for buttons
    "light_button_hover": "#3674B5",   # Dark blue for button hover
    "light_settings_bg": "#D1F8EF",    # Lightest turquoise for settings
    "light_settings_button": "#578FCA"  # Medium blue for settings buttons
}

class ModernButton(ctk.CTkButton):
    def __init__(self, *args, **kwargs):
        # Remove padding from kwargs before passing to super()
        if 'pady' in kwargs: del kwargs['pady']
        if 'padx' in kwargs: del kwargs['padx']
        
        super().__init__(*args, **kwargs)
        self.configure(
            corner_radius=8,
            height=40,
            font=("Inter", 14, "bold"),
            hover_color=COLORS["button_hover"]
        )
        # Add padding to the button's container instead
        self.pack_configure(pady=5, padx=10)

class TranslatorApp:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("LinguaSync")
        self.window.geometry("1200x800")
        self.window.configure(fg_color=COLORS["bg_primary"])
        
        # Initialize variables
        self.is_running = False
        self.is_recording = False
        self.is_dark_theme = True
        
        # Add settings state tracking
        self.current_voice = None
        self.current_speed = 150
        self.current_volume = 1.0
        
        # Initialize text-to-speech engine
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.current_speed)
        self.engine.setProperty('volume', self.current_volume)
        
        # Create main container
        self.create_layout()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_layout(self):
        # Header section
        self.header = ctk.CTkFrame(self.window, fg_color="transparent")
        self.header.pack(fill="x", padx=40, pady=(30, 20))
        
        # Logo and title
        self.title = ctk.CTkLabel(
            self.header,
            text="LinguaSync",
            font=("Inter", 32, "bold"),
            text_color=COLORS["accent"]
        )
        self.title.pack(side="left")
        
        # Subtitle
        self.subtitle = ctk.CTkLabel(
            self.header,
            text="Real-Time Voice Translation",
            font=("Inter", 16),
            text_color=COLORS["text_secondary"]
        )
        self.subtitle.pack(side="left", padx=20)
        
        # Add settings button
        self.create_settings_button()
        
        # Main content area
        self.content = ctk.CTkFrame(
            self.window,
            fg_color=COLORS["bg_secondary"],
            corner_radius=15
        )
        self.content.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        
        # Create components in correct order
        self.create_controls()
        self.create_language_selector()
        self.create_translation_area()

    def create_language_selector(self):
        self.lang_frame = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        self.lang_frame.pack(fill="x", padx=30, pady=20)
        
        # Language selection with modern styling
        for side, label, default in [("left", "From", "English"), ("right", "To", "Hindi")]:
            frame = ctk.CTkFrame(self.lang_frame, fg_color="transparent")
            frame.pack(side=side, expand=True, padx=20)
            
            label = ctk.CTkLabel(
                frame,
                text=label,
                font=("Inter", 14),
                text_color=COLORS["text_secondary"]
            )
            label.pack(pady=(0, 5))
            
            selector = ctk.CTkOptionMenu(
                frame,
                values=list(LANGUAGE_CODES.keys()),
                width=200,
                height=35,
                corner_radius=8,
                font=("Inter", 13),
                fg_color=COLORS["bg_primary"],
                button_color=COLORS["accent"],
                button_hover_color=COLORS["button_hover"],
                text_color=COLORS["text_primary"],
                dropdown_fg_color=COLORS["bg_primary"],
                dropdown_text_color=COLORS["text_primary"],
                dropdown_hover_color=COLORS["button_hover"]
            )
            selector.pack()
            selector.set(default)
            
            if side == "left":
                self.input_lang = selector
            else:
                self.output_lang = selector

    def create_translation_area(self):
        # Text area container
        self.text_container = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        self.text_container.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        
        # Input and output text areas
        for side, label in [("left", "Original Text"), ("right", "Translated Text")]:
            frame = ctk.CTkFrame(
                self.text_container,
                fg_color=COLORS["bg_primary"],
                corner_radius=10
            )
            frame.pack(side=side, fill="both", expand=True, padx=10)
            
            label = ctk.CTkLabel(
                frame,
                text=label,
                font=("Inter", 14),
                text_color=COLORS["text_secondary"]
            )
            label.pack(pady=10)
            
            text_box = ctk.CTkTextbox(
                frame,
                font=("Inter", 14),
                text_color=COLORS["text_primary"],
                fg_color=COLORS["bg_primary"],
                corner_radius=0,
                border_spacing=10,
                wrap="word",
                height=200  # Set a fixed height
            )
            text_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            
            # Make text box read-only
            text_box.configure(state="normal")
            text_box.delete("0.0", "end")
            text_box.insert("0.0", f"Your {label.lower()} will appear here...")
            text_box.configure(state="normal")
            
            if side == "left":
                self.input_text = text_box
            else:
                self.output_text = text_box

    def create_controls(self):
        self.control_frame = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        self.control_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        # Add mode toggle
        self.create_input_mode_toggle()
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            self.control_frame,
            text="Ready to translate",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", padx=10)
        
        # Control buttons
        self.start_button = ModernButton(
            self.control_frame,
            text="Start Speaking",
            fg_color=COLORS["accent"],
            command=self.start_translation
        )
        self.start_button.pack(side="right", padx=10)
        
        self.stop_button = ModernButton(
            self.control_frame,
            text="Stop",
            fg_color=COLORS["error"],
            command=self.stop_translation,
            state="disabled"
        )
        self.stop_button.pack(side="right", padx=10)

    def create_input_mode_toggle(self):
        self.mode_frame = ctk.CTkFrame(
            self.control_frame,
            fg_color="transparent"
        )
        self.mode_frame.pack(side="left", padx=20)
        
        self.mode_label = ctk.CTkLabel(
            self.mode_frame,
            text="Input Mode:",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        )
        self.mode_label.pack(side="left", padx=(0, 10))
        
        self.mode_button = ModernButton(
            self.mode_frame,
            text="🎤 Voice",
            width=120,
            fg_color=COLORS["mode_toggle"],
            command=self.toggle_input_mode
        )
        self.mode_button.pack(side="left")
        
        self.is_voice_mode = True

    def toggle_input_mode(self):
        self.is_voice_mode = not self.is_voice_mode
        self.mode_button.configure(
            text="🎤 Voice" if self.is_voice_mode else "⌨️ Text",
            fg_color=COLORS["mode_toggle"]
        )
        self.start_button.configure(
            text="Start Speaking" if self.is_voice_mode else "Translate Text"
        )
        self.input_text.configure(state="disabled" if self.is_voice_mode else "normal")
        
        if self.is_voice_mode:
            self.input_text.delete("0.0", "end")
            self.input_text.insert("0.0", "Your original text will appear here...")
        else:
            self.input_text.delete("0.0", "end")
            self.input_text.insert("0.0", "Type your text here...")

    def update_status(self, message, is_error=False):
        self.status_label.configure(
            text=message,
            text_color=COLORS["error"] if is_error else COLORS["text_primary"]
        )

    def start_translation(self):
        if not self.is_voice_mode:
            # Text input mode
            try:
                input_text = self.input_text.get("0.0", "end").strip()
                if not input_text or input_text == "Type your text here...":
                    self.update_status("Please enter text to translate", True)
                    return
                
                input_lang_code = LANGUAGE_CODES[self.input_lang.get()]
                output_lang_code = LANGUAGE_CODES[self.output_lang.get()]
                
                self.update_status("Translating...")
                translated_text = GoogleTranslator(
                    source=input_lang_code,
                    target=output_lang_code
                ).translate(text=input_text)
                
                # Update output text
                self.output_text.delete("0.0", "end")
                self.output_text.insert("0.0", translated_text)
                
                # Generate audio
                self.speak_text(translated_text, output_lang_code)
                
                self.update_status("Translation complete")
                
            except Exception as e:
                self.update_status(f"Error: {str(e)}", True)
        else:
            # Voice input mode (existing functionality)
            if not self.is_running:
                self.is_running = True
                self.start_button.configure(state="disabled")
                self.stop_button.configure(state="normal")
                threading.Thread(target=self.translation_loop, daemon=True).start()

    def stop_translation(self):
        self.is_running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.update_status("Ready")

    def translation_loop(self):
        r = sr.Recognizer()
        
        while self.is_running:
            try:
                self.update_status("Listening...")
                with sr.Microphone() as source:
                    # Adjust for ambient noise
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source)
                
                self.update_status("Processing speech...")
                speech_text = r.recognize_google(audio)
                
                # Clear and update input text
                self.window.after(0, lambda: self.input_text.delete("0.0", "end"))
                self.window.after(0, lambda: self.input_text.insert("0.0", speech_text))
                
                if speech_text.lower() in ['exit', 'stop']:
                    self.stop_translation()
                    return
                
                input_lang_code = LANGUAGE_CODES[self.input_lang.get()]
                output_lang_code = LANGUAGE_CODES[self.output_lang.get()]
                
                self.update_status("Translating...")
                translated_text = GoogleTranslator(
                    source=input_lang_code,
                    target=output_lang_code
                ).translate(text=speech_text)
                
                # Clear and update output text
                self.window.after(0, lambda: self.output_text.delete("0.0", "end"))
                self.window.after(0, lambda: self.output_text.insert("0.0", translated_text))
                
                # Text-to-speech
                self.speak_text(translated_text, output_lang_code)
                
                self.update_status("Ready")
                
            except sr.UnknownValueError:
                self.update_status("Could not understand audio", True)
            except sr.RequestError as e:
                self.update_status(f"Could not request results: {str(e)}", True)
            except Exception as e:
                self.update_status(f"Error: {str(e)}", True)

    def on_closing(self):
        self.stop_translation()
        self.window.destroy()

    def run(self):
        self.window.mainloop()

    def set_theme(self, is_dark):
        self.is_dark_theme = is_dark
        theme_colors = COLORS if is_dark else {
            "bg_primary": COLORS["light_bg_primary"],
            "bg_secondary": COLORS["light_bg_secondary"],
            "text_primary": COLORS["light_text_primary"],
            "text_secondary": COLORS["light_text_secondary"],
            "frame": COLORS["light_frame"],
            "accent": COLORS["light_accent"],
            "error": COLORS["error"],
            "success": COLORS["success"],
            "button_hover": COLORS["light_button_hover"],
            "settings_bg": COLORS["light_settings_bg"],
            "settings_button": COLORS["light_settings_button"]
        }
        
        # Update UI colors
        self.window.configure(fg_color=theme_colors["bg_primary"])
        self.content.configure(fg_color=theme_colors["bg_secondary"])
        self.header.configure(fg_color=theme_colors["bg_primary"])
        
        # Update all text colors
        self.title.configure(text_color=theme_colors["accent"])
        self.subtitle.configure(text_color=theme_colors["text_secondary"])
        self.status_label.configure(text_color=theme_colors["text_primary"])
        
        # Update buttons
        self.start_button.configure(
            fg_color=theme_colors["accent"],
            hover_color=theme_colors["button_hover"]
        )
        self.stop_button.configure(
            hover_color=theme_colors["button_hover"]
        )
        self.settings_button.configure(
            fg_color=theme_colors["settings_button"],
            hover_color=theme_colors["button_hover"]
        )
        self.mode_button.configure(
            fg_color=theme_colors["settings_button"],
            hover_color=theme_colors["button_hover"]
        )
        
        # Update text areas and their containers
        for text_box in [self.input_text, self.output_text]:
            text_box.configure(
                fg_color=theme_colors["bg_primary"],
                text_color=theme_colors["text_primary"]
            )
            # Get the parent frame and update its color
            text_frame = text_box.winfo_parent()
            if text_frame:
                self.window.nametowidget(text_frame).configure(fg_color=theme_colors["frame"])

        # Update language selectors
        for selector in [self.input_lang, self.output_lang]:
            selector.configure(
                fg_color=theme_colors["bg_primary"],
                text_color=theme_colors["text_primary"],
                button_color=theme_colors["accent"],
                button_hover_color=theme_colors["button_hover"],
                dropdown_fg_color=theme_colors["bg_primary"],
                dropdown_text_color=theme_colors["text_primary"],
                dropdown_hover_color=theme_colors["button_hover"]
            )

    def create_settings_button(self):
        self.settings_button = ModernButton(
            self.header,
            text="⚙️",
            width=40,
            fg_color=COLORS["settings_button"],
            command=self.show_settings
        )
        self.settings_button.pack(side="right", padx=20)

    def show_settings(self):
        self.settings_popup = SettingsPopup(self.window, self)

    def set_volume(self, volume):
        try:
            volume_fraction = volume / 100.0
            self.engine.setProperty('volume', volume_fraction)
        except Exception as e:
            self.update_status(f"Error setting volume: {str(e)}", True)

    def speak_text(self, text, lang_code):
        try:
            if lang_code == 'en':  # Use pyttsx3 for English
                # Ensure current settings are applied
                if self.current_voice:
                    self.engine.setProperty('voice', self.current_voice)
                self.engine.setProperty('rate', self.current_speed)
                self.engine.setProperty('volume', self.current_volume)
                
                # Create new engine instance to ensure settings are applied
                temp_engine = pyttsx3.init()
                temp_engine.setProperty('rate', self.current_speed)
                temp_engine.setProperty('volume', self.current_volume)
                if self.current_voice:
                    temp_engine.setProperty('voice', self.current_voice)
                
                # Speak using temporary engine
                temp_engine.say(text)
                temp_engine.runAndWait()
                temp_engine.stop()
                
            else:  # Use gTTS for other languages
                voice = gTTS(text, lang=lang_code)
                voice.save('temp.mp3')
                playsound('temp.mp3')
                os.remove('temp.mp3')
                
        except Exception as e:
            self.update_status(f"Error in speech: {str(e)}", True)
            print(f"Speech error details: {str(e)}")

    # Add this method to handle speed changes
    def change_speed(self, speed):
        try:
            speed_value = int(speed)
            self.engine.setProperty('rate', speed_value)
        except Exception as e:
            print(f"Error changing speed: {e}")

# Add this class for the settings popup
class SettingsPopup:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        
        # Create semi-transparent overlay
        self.overlay = ctk.CTkFrame(
            parent,
            fg_color=COLORS["overlay"]
        )
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.overlay.configure(fg_color=(COLORS["overlay"], COLORS["overlay"]))
        
        # Create popup frame
        self.popup = ctk.CTkFrame(
            self.overlay,
            fg_color=COLORS["settings_bg"] if app.is_dark_theme else COLORS["light_settings_bg"],
            corner_radius=15
        )
        self.popup.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.4, relheight=0.6)
        
        # Title
        self.title = ctk.CTkLabel(
            self.popup,
            text="Settings",
            font=("Inter", 24, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.title.pack(pady=20)
        
        # Initialize with current settings
        self.current_settings = {
            'speed': app.current_speed,
            'volume': app.current_volume * 100,  # Convert to percentage
            'voice': app.current_voice
        }
        
        # Settings container
        self.settings_container = ctk.CTkFrame(
            self.popup,
            fg_color="transparent"
        )
        self.settings_container.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Voice settings
        self.create_voice_settings()
        
        # Speed settings
        self.create_speed_settings()
        
        # Volume settings
        self.create_volume_settings()
        
        # Theme toggle
        self.create_theme_toggle()
        
        # Close button with proper padding
        close_button_frame = ctk.CTkFrame(
            self.popup,
            fg_color="transparent"
        )
        close_button_frame.pack(pady=20)
        
        self.close_button = ModernButton(
            close_button_frame,
            text="Close",
            fg_color=COLORS["error"],
            hover_color=COLORS["light_button_hover"] if not app.is_dark_theme else COLORS["button_hover"],
            command=self.close
        )
        self.close_button.pack()
        
        # Update theme switch based on current theme
        self.theme_switch.select() if app.is_dark_theme else self.theme_switch.deselect()
        
        # Update popup colors based on theme
        popup_bg = COLORS["settings_bg"] if app.is_dark_theme else COLORS["light_settings_bg"]
        self.popup.configure(fg_color=popup_bg)
        
        # Update theme switch colors
        self.theme_switch.configure(
            button_color=COLORS["light_accent"] if not app.is_dark_theme else COLORS["accent"],
            button_hover_color=COLORS["light_button_hover"] if not app.is_dark_theme else COLORS["button_hover"],
            fg_color=COLORS["light_settings_button"] if not app.is_dark_theme else COLORS["settings_button"]
        )
        
    def create_voice_settings(self):
        frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        frame.pack(fill="x", pady=10)
        
        label = ctk.CTkLabel(
            frame,
            text="🔊 Voice Type:",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        )
        label.pack(side="left")
        
        try:
            # Get available voices and categorize them
            voices = self.app.engine.getProperty('voices')
            voice_options = []
            self.voice_map = {}
            
            for voice in voices:
                name = voice.name.lower()
                if "david" in name or "mark" in name or "james" in name:
                    label = f"Male ({voice.name.split()[-2]})"
                elif "zira" in name or "helen" in name:
                    label = f"Female ({voice.name.split()[-2]})"
                else:
                    # Include all voices with their names
                    label = f"Voice ({voice.name.split()[-2] if len(voice.name.split()) > 2 else voice.name})"
                
                voice_options.append(label)
                self.voice_map[label] = voice
            
            if not voice_options:
                voice_options = ["Default"]
                self.voice_map["Default"] = voices[0]
            
            self.voice_selector = ctk.CTkOptionMenu(
                frame,
                values=voice_options,
                width=200,
                font=("Inter", 13),
                command=self.change_voice
            )
            self.voice_selector.pack(side="right")
            self.voice_selector.set(voice_options[0])
            
        except Exception as e:
            print(f"Error initializing voices: {e}")
            # Create a disabled selector if voices can't be loaded
            self.voice_selector = ctk.CTkOptionMenu(
                frame,
                values=["No voices found"],
                width=200,
                font=("Inter", 13),
                state="disabled"
            )
            self.voice_selector.pack(side="right")
        
    def create_speed_settings(self):
        frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        frame.pack(fill="x", pady=10)
        
        label = ctk.CTkLabel(
            frame,
            text="⚡ Speed:",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        )
        label.pack(side="left")
        
        self.speed_value = ctk.CTkLabel(
            frame,
            text="150",
            width=40,
            font=("Inter", 14),
            text_color=COLORS["accent"]
        )
        self.speed_value.pack(side="right", padx=10)
        
        self.speed_slider = ctk.CTkSlider(
            frame,
            from_=50,
            to=300,
            number_of_steps=250,
            width=200,
            command=self.update_speed
        )
        self.speed_slider.pack(side="right")
        
        # Set initial value from current settings
        self.speed_slider.set(self.current_settings['speed'])
        self.speed_value.configure(text=str(self.current_settings['speed']))
        
    def create_volume_settings(self):
        frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        frame.pack(fill="x", pady=10)
        
        label = ctk.CTkLabel(
            frame,
            text="🔈 Volume:",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        )
        label.pack(side="left")
        
        self.volume_value = ctk.CTkLabel(
            frame,
            text="100%",
            width=40,
            font=("Inter", 14),
            text_color=COLORS["accent"]
        )
        self.volume_value.pack(side="right", padx=10)
        
        self.volume_slider = ctk.CTkSlider(
            frame,
            from_=0,
            to=100,
            number_of_steps=100,
            width=200,
            command=self.update_volume
        )
        self.volume_slider.pack(side="right")
        
        # Set initial value from current settings
        self.volume_slider.set(self.current_settings['volume'])
        self.volume_value.configure(text=f"{int(self.current_settings['volume'])}%")
        
    def create_theme_toggle(self):
        frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        frame.pack(fill="x", pady=10)
        
        label = ctk.CTkLabel(
            frame,
            text="🌓 Theme:",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        )
        label.pack(side="left")
        
        self.theme_switch = ctk.CTkSwitch(
            frame,
            text="Dark Mode",
            command=self.toggle_theme,
            font=("Inter", 13)
        )
        self.theme_switch.pack(side="right")
        
    def update_speed(self, value):
        speed = int(value)
        self.speed_value.configure(text=str(speed))
        self.app.current_speed = speed
        self.app.engine.setProperty('rate', speed)
        
    def update_volume(self, value):
        volume = int(value)
        volume_fraction = volume / 100.0
        self.volume_value.configure(text=f"{volume}%")
        self.app.current_volume = volume_fraction
        self.app.engine.setProperty('volume', volume_fraction)
        
    def toggle_theme(self):
        is_dark = self.theme_switch.get()
        self.app.set_theme(is_dark)
        
    def change_voice(self, voice_name):
        try:
            if voice_name in self.voice_map:
                voice = self.voice_map[voice_name]
                self.app.current_voice = voice.id
                
                # Create temporary engine for testing
                temp_engine = pyttsx3.init()
                temp_engine.setProperty('voice', voice.id)
                temp_engine.setProperty('rate', self.app.current_speed)
                temp_engine.setProperty('volume', self.app.current_volume)
                
                # Test with current settings
                temp_engine.say("Voice changed")
                temp_engine.runAndWait()
                temp_engine.stop()
                
                # Update main engine
                self.app.engine.setProperty('voice', voice.id)
                print(f"Voice changed to: {voice_name}")
        except Exception as e:
            print(f"Error changing voice: {e}")
        
    def close(self):
        self.overlay.destroy()

if __name__ == "__main__":
    app = TranslatorApp()
    app.run() 