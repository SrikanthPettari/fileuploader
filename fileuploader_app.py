#!/usr/bin/env python3
"""
Artifactory File Uploader GUI
Author: Srikanth Pettari
Description: A GUI-based file uploader for Artifactory using ttkbootstrap and requests
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import requests
import subprocess
import os
import json
import base64
from datetime import datetime
import threading
import math


class CircularProgressBar(tk.Canvas):
    """Custom circular progress bar with status indicator"""
    
    def __init__(self, parent, size=150, bg_color="#222222", **kwargs):
        super().__init__(parent, width=size, height=size, bg=bg_color, 
                        highlightthickness=0, **kwargs)
        self.size = size
        self.progress = 0
        self.status = "idle"  # idle, uploading, success, failed
        self.status_text = ""
        self.bg_color = bg_color
    
    def draw_progress(self):
        """Draw the circular progress bar"""
        self.delete("all")
        
        center = self.size / 2
        radius = self.size / 2 - 10
        
        # Draw background circle
        self.create_oval(
            center - radius, center - radius,
            center + radius, center + radius,
            outline="#444444", width=3, fill="#1a1a1a"
        )
        
        # Draw progress arc
        if self.progress > 0:
            angle = (self.progress / 100) * 360
            self.create_arc(
                center - radius, center - radius,
                center + radius, center + radius,
                start=90, extent=-angle,
                outline="#00FF00" if self.status == "success" else 
                        "#FF0000" if self.status == "failed" else "#0099FF",
                width=4, style="arc"
            )
        
        # Draw status icon in center
        if self.status == "uploading":
            # Draw spinning indicator
            angle = (self.progress % 100) / 100 * 360
            x1 = center + radius * 0.6 * math.cos(math.radians(angle - 90))
            y1 = center + radius * 0.6 * math.sin(math.radians(angle - 90))
            self.create_line(center, center, x1, y1, fill="#0099FF", width=3)
            self.create_text(center, center + radius * 0.2, text="Uploading...",
                           fill="#0099FF", font=("Arial", 10, "bold"))
        
        elif self.status == "success":
            # Draw checkmark
            checkmark_start_x = center - radius * 0.3
            checkmark_start_y = center + radius * 0.1
            checkmark_mid_x = center - radius * 0.1
            checkmark_mid_y = center + radius * 0.25
            checkmark_end_x = center + radius * 0.25
            checkmark_end_y = center - radius * 0.15
            
            self.create_line(
                checkmark_start_x, checkmark_start_y,
                checkmark_mid_x, checkmark_mid_y,
                checkmark_end_x, checkmark_end_y,
                fill="#00FF00", width=4
            )
            self.create_text(center, center + radius * 0.45, text="Success!",
                           fill="#00FF00", font=("Arial", 11, "bold"))
        
        elif self.status == "failed":
            # Draw X mark
            offset = radius * 0.2
            self.create_line(
                center - offset, center - offset,
                center + offset, center + offset,
                fill="#FF0000", width=4
            )
            self.create_line(
                center + offset, center - offset,
                center - offset, center + offset,
                fill="#FF0000", width=4
            )
            self.create_text(center, center + radius * 0.45, text="Failed!",
                           fill="#FF0000", font=("Arial", 11, "bold"))
        
        else:  # idle
            self.create_text(center, center, text="Ready",
                           fill="#AAAAAA", font=("Arial", 11, "bold"))
    
    def set_progress(self, value, status="uploading"):
        """Update progress"""
        self.progress = max(0, min(100, value))
        self.status = status
        self.draw_progress()
        self.update()
    
    def set_status(self, status, text=""):
        """Set status (idle, uploading, success, failed)"""
        self.status = status
        self.status_text = text
        if status == "idle":
            self.progress = 0
        elif status == "success":
            self.progress = 100
        elif status == "failed":
            self.progress = 100
        self.draw_progress()
        self.update()


class ArtifactoryUploader:
    """Artifactory File Upload Manager"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Artifactory File Uploader")
        self.root.geometry("1000x900")
        self.root.resizable(True, True)
        
        # Theme selection
        self.theme_var = tk.StringVar(value="darkly")
        
        # Variables
        self.artifactory_url = tk.StringVar(value="https://artifactory.example.com")
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.source_file = tk.StringVar()
        self.destination_path = tk.StringVar(value="/artifactory/repo-name/")
        self.api_token = tk.StringVar()
        self.upload_status = tk.StringVar(value="Ready")
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=15, pady=15)
        
        # ===== THEME SELECTOR =====
        theme_frame = ttk.LabelFrame(main_frame, text="Theme Settings")
        theme_frame.pack(fill=X, pady=(0, 15), padx=10, ipady=10)
        
        theme_label = ttk.Label(theme_frame, text="Select Theme:")
        theme_label.pack(side=LEFT, padx=5)
        
        themes = ["darkly", "solar", "superhero", "cyborg", "vapor"]
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                    values=themes, state="readonly", width=15)
        theme_combo.pack(side=LEFT, padx=5)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # ===== ARTIFACTORY CONFIGURATION =====
        config_frame = ttk.LabelFrame(main_frame, text="Artifactory Configuration")
        config_frame.pack(fill=X, pady=(0, 15), padx=10, ipady=10)
        
        # Artifactory URL
        ttk.Label(config_frame, text="Artifactory URL:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0), padx=10)
        ttk.Entry(config_frame, textvariable=self.artifactory_url, width=60).pack(fill=X, pady=(0, 10), padx=10)
        
        # ===== CREDENTIALS SECTION =====
        credentials_frame = ttk.LabelFrame(main_frame, text="Authentication")
        credentials_frame.pack(fill=X, pady=(0, 15), padx=10, ipady=10)
        
        # Username
        ttk.Label(credentials_frame, text="Username:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0), padx=10)
        ttk.Entry(credentials_frame, textvariable=self.username, width=60).pack(fill=X, pady=(0, 10), padx=10)
        
        # Password
        ttk.Label(credentials_frame, text="Password:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0), padx=10)
        password_entry = ttk.Entry(credentials_frame, textvariable=self.password, width=60, show="•")
        password_entry.pack(fill=X, pady=(0, 10), padx=10)
        
        # Token Generation Button
        ttk.Button(credentials_frame, text="Generate API Token", 
                  command=self.generate_token, bootstyle="info").pack(anchor=W, pady=(5, 0), padx=10)
        
        # API Token Display
        ttk.Label(credentials_frame, text="Generated Token:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(10, 0), padx=10)
        token_entry = ttk.Entry(credentials_frame, textvariable=self.api_token, 
                               width=60, state="readonly")
        token_entry.pack(fill=X, pady=(0, 5), padx=10)
        
        # ===== FILE SELECTION SECTION =====
        file_frame = ttk.LabelFrame(main_frame, text="File Selection")
        file_frame.pack(fill=X, pady=(0, 15), padx=10, ipady=10)
        
        # Source File
        ttk.Label(file_frame, text="Source File:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0), padx=10)
        source_frame = ttk.Frame(file_frame)
        source_frame.pack(fill=X, pady=(0, 10), padx=10)
        
        ttk.Entry(source_frame, textvariable=self.source_file, width=50).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(source_frame, text="Browse", command=self.browse_file, bootstyle="success").pack(side=LEFT)
        
        # Destination Path
        ttk.Label(file_frame, text="Destination Path (in Artifactory):", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0), padx=10)
        dest_frame = ttk.Frame(file_frame)
        dest_frame.pack(fill=X, pady=(0, 5), padx=10)
        
        ttk.Entry(dest_frame, textvariable=self.destination_path, width=50).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(dest_frame, text="Copy", command=self.copy_to_clipboard, bootstyle="warning").pack(side=LEFT)
        
        # ===== ACTION BUTTONS =====
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=X, pady=(0, 15), padx=10)
        
        ttk.Button(action_frame, text="Upload to Artifactory", command=self.upload_file, 
                  bootstyle="danger", width=20).pack(side=LEFT, padx=5)
        ttk.Button(action_frame, text="Clear All", command=self.clear_fields, 
                  bootstyle="secondary", width=20).pack(side=LEFT, padx=5)
        
        # ===== STATUS SECTION WITH CIRCULAR PROGRESS =====
        status_frame = ttk.LabelFrame(main_frame, text="Upload Status")
        status_frame.pack(fill=BOTH, expand=True, padx=10, ipady=10)
        
        # Circular progress bar
        progress_container = ttk.Frame(status_frame)
        progress_container.pack(pady=15)
        
        self.progress_canvas = CircularProgressBar(progress_container, size=180, bg_color="#222222")
        self.progress_canvas.pack()
        
        # Status label
        ttk.Label(status_frame, textvariable=self.upload_status, 
                 font=("Arial", 11, "bold"), foreground="cyan").pack(anchor=CENTER, pady=(10, 10))
        
        # Log display
        log_label = ttk.Label(status_frame, text="Activity Log:", font=("Arial", 10, "bold"))
        log_label.pack(anchor=W, pady=(10, 5), padx=10)
        
        self.log_text = scrolledtext.ScrolledText(status_frame, height=8, width=100, 
                                                   state=DISABLED, font=("Courier", 9))
        self.log_text.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
    
    def change_theme(self, event=None):
        """Change application theme"""
        theme = self.theme_var.get()
        try:
            style = ttk.Style()
            style.theme_use(theme)
            self.log_message(f"✓ Theme changed to: {theme}", "success")
        except Exception as e:
            messagebox.showerror("Theme Error", f"Failed to change theme: {str(e)}")
    
    def generate_token(self):
        """Generate API token using username and password"""
        username = self.username.get().strip()
        password = self.password.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter username and password")
            return
        
        credentials = f"{username}:{password}"
        base64_credentials = base64.b64encode(credentials.encode()).decode()
        
        # Using curl command via subprocess
        url = f"{self.artifactory_url.get()}/api/security/apiKey"
        
        try:
            self.log_message("Generating API token...", "info")
            
            curl_command = [
                "curl",
                "-X", "GET",
                "-H", f"Authorization: Basic {base64_credentials}",
                "-s",
                url
            ]
            
            result = subprocess.run(curl_command, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                try:
                    response_data = json.loads(result.stdout)
                    token = response_data.get("apiKey", "")
                    
                    if token:
                        self.api_token.set(token)
                        self.log_message(f"✓ Token generated successfully!", "success")
                        messagebox.showinfo("Success", "API Token generated successfully!")
                    else:
                        raise ValueError("No token in response")
                except json.JSONDecodeError:
                    self.log_message(f"✗ Failed to parse token response: {result.stdout}", "error")
                    messagebox.showerror("Error", "Invalid response format from server")
            else:
                self.log_message(f"✗ Token generation failed: {result.stderr}", "error")
                messagebox.showerror("Error", f"Failed to generate token: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            self.log_message("✗ Request timeout while generating token", "error")
            messagebox.showerror("Error", "Request timeout")
        except Exception as e:
            self.log_message(f"✗ Token generation error: {str(e)}", "error")
            messagebox.showerror("Error", f"Error generating token: {str(e)}")
    
    def browse_file(self):
        """Browse and select a file"""
        file_path = filedialog.askopenfilename(
            title="Select File to Upload",
            initialdir=os.path.expanduser("~"),
            filetypes=[("All Files", "*.*"), ("Text Files", "*.txt"), ("Archives", "*.zip *.tar *.gz")]
        )
        
        if file_path:
            self.source_file.set(file_path)
            self.log_message(f"File selected: {file_path}", "success")
    
    def copy_to_clipboard(self):
        """Copy destination path to clipboard"""
        dest_path = self.destination_path.get()
        if dest_path:
            self.root.clipboard_clear()
            self.root.clipboard_append(dest_path)
            messagebox.showinfo("Success", "Destination path copied to clipboard!")
        else:
            messagebox.showwarning("Error", "Destination path is empty")
    
    def upload_file(self):
        """Upload file to Artifactory"""
        # Validate inputs
        source_file = self.source_file.get().strip()
        destination_path = self.destination_path.get().strip()
        api_token = self.api_token.get().strip()
        
        if not source_file or not os.path.exists(source_file):
            messagebox.showerror("Error", "Please select a valid source file")
            return
        
        if not destination_path:
            messagebox.showerror("Error", "Please specify destination path")
            return
        
        if not api_token:
            messagebox.showerror("Error", "Please generate API token first")
            return
        
        # Set progress to uploading
        self.progress_canvas.set_status("uploading")
        self.upload_status.set("Uploading...")
        
        # Run upload in separate thread
        upload_thread = threading.Thread(
            target=self._perform_upload,
            args=(source_file, destination_path, api_token)
        )
        upload_thread.daemon = True
        upload_thread.start()
    
    def _perform_upload(self, source_file, destination_path, api_token):
        """Perform the actual file upload"""
        try:
            self.log_message(f"Starting upload: {os.path.basename(source_file)}", "info")
            
            # Prepare upload URL
            artifactory_url = self.artifactory_url.get().rstrip("/")
            destination_path = destination_path.lstrip("/")
            upload_url = f"{artifactory_url}/{destination_path}{os.path.basename(source_file)}"
            
            # Upload using requests library
            with open(source_file, 'rb') as f:
                file_content = f.read()
            
            headers = {
                "X-JFrog-Art-Api": api_token,
                "Content-Type": "application/octet-stream"
            }
            
            self.log_message(f"Upload URL: {upload_url}", "info")
            file_size_mb = len(file_content) / (1024*1024)
            self.log_message(f"File size: {file_size_mb:.2f} MB", "info")
            
            # Simulate progress updates
            for progress in range(0, 90, 10):
                self.progress_canvas.set_progress(progress, "uploading")
                self.root.update()
                import time
                time.sleep(0.1)
            
            response = requests.put(
                upload_url,
                data=file_content,
                headers=headers,
                timeout=30,
                verify=False  # For self-signed certificates
            )
            
            if response.status_code in [200, 201]:
                self.progress_canvas.set_status("success")
                self.log_message(f"✓ Upload successful! Status: {response.status_code}", "success")
                self.upload_status.set(f"✓ Upload completed - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                messagebox.showinfo("Success", "File uploaded successfully to Artifactory!")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.progress_canvas.set_status("failed")
                self.log_message(f"✗ Upload failed: {error_msg}", "error")
                self.upload_status.set("✗ Upload failed")
                messagebox.showerror("Upload Failed", error_msg)
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            self.progress_canvas.set_status("failed")
            self.log_message(f"✗ {error_msg}", "error")
            self.upload_status.set("✗ Upload failed - Network error")
            messagebox.showerror("Error", error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.progress_canvas.set_status("failed")
            self.log_message(f"✗ {error_msg}", "error")
            self.upload_status.set("✗ Upload failed")
            messagebox.showerror("Error", error_msg)
    
    def clear_fields(self):
        """Clear all input fields"""
        confirm = messagebox.askyesno("Confirm", "Clear all fields?")
        if confirm:
            self.username.set("")
            self.password.set("")
            self.source_file.set("")
            self.destination_path.set("/artifactory/repo-name/")
            self.api_token.set("")
            self.upload_status.set("Ready")
            self.progress_canvas.set_status("idle")
            self.log_message("All fields cleared", "info")
    
    def log_message(self, message, msg_type="info"):
        """Add message to log display"""
        self.log_text.config(state=NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.log_text.config(state=DISABLED)


def main():
    """Main application entry point"""
    root = ttk.Window(themename="darkly")
    app = ArtifactoryUploader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
