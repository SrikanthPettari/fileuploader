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


class ArtifactoryUploader:
    """Artifactory File Upload Manager"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Artifactory File Uploader")
        self.root.geometry("900x750")
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
        
        # Create main frame with padding
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=BOTH, expand=True)
        
        # ===== THEME SELECTOR =====
        theme_frame = ttk.LabelFrame(main_frame, text="Theme Settings", padding=10)
        theme_frame.pack(fill=X, pady=(0, 15))
        
        theme_label = ttk.Label(theme_frame, text="Select Theme:")
        theme_label.pack(side=LEFT, padx=5)
        
        themes = ["darkly", "solar", "superhero", "cyborg", "vapor"]
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                    values=themes, state="readonly", width=15)
        theme_combo.pack(side=LEFT, padx=5)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # ===== ARTIFACTORY CONFIGURATION =====
        config_frame = ttk.LabelFrame(main_frame, text="Artifactory Configuration", padding=10)
        config_frame.pack(fill=X, pady=(0, 15))
        
        # Artifactory URL
        ttk.Label(config_frame, text="Artifactory URL:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0))
        ttk.Entry(config_frame, textvariable=self.artifactory_url, width=60).pack(fill=X, pady=(0, 10))
        
        # ===== CREDENTIALS SECTION =====
        credentials_frame = ttk.LabelFrame(main_frame, text="Authentication", padding=10)
        credentials_frame.pack(fill=X, pady=(0, 15))
        
        # Username
        ttk.Label(credentials_frame, text="Username:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0))
        ttk.Entry(credentials_frame, textvariable=self.username, width=60).pack(fill=X, pady=(0, 10))
        
        # Password
        ttk.Label(credentials_frame, text="Password:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0))
        password_entry = ttk.Entry(credentials_frame, textvariable=self.password, width=60, show="•")
        password_entry.pack(fill=X, pady=(0, 10))
        
        # Token Generation Button
        ttk.Button(credentials_frame, text="Generate API Token", 
                  command=self.generate_token, bootstyle="info").pack(anchor=W, pady=(5, 0))
        
        # API Token Display
        ttk.Label(credentials_frame, text="Generated Token:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(10, 0))
        token_entry = ttk.Entry(credentials_frame, textvariable=self.api_token, 
                               width=60, state="readonly")
        token_entry.pack(fill=X, pady=(0, 5))
        
        # ===== FILE SELECTION SECTION =====
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding=10)
        file_frame.pack(fill=X, pady=(0, 15))
        
        # Source File
        ttk.Label(file_frame, text="Source File:", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0))
        source_frame = ttk.Frame(file_frame)
        source_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Entry(source_frame, textvariable=self.source_file, width=50).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(source_frame, text="Browse", command=self.browse_file, bootstyle="success").pack(side=LEFT)
        
        # Destination Path
        ttk.Label(file_frame, text="Destination Path (in Artifactory):", font=("Arial", 10, "bold")).pack(anchor=W, pady=(5, 0))
        dest_frame = ttk.Frame(file_frame)
        dest_frame.pack(fill=X, pady=(0, 5))
        
        ttk.Entry(dest_frame, textvariable=self.destination_path, width=50).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(dest_frame, text="Copy", command=self.copy_to_clipboard, bootstyle="warning").pack(side=LEFT)
        
        # ===== ACTION BUTTONS =====
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Button(action_frame, text="Upload to Artifactory", command=self.upload_file, 
                  bootstyle="danger", width=20).pack(side=LEFT, padx=5)
        ttk.Button(action_frame, text="Clear All", command=self.clear_fields, 
                  bootstyle="secondary", width=20).pack(side=LEFT, padx=5)
        
        # ===== STATUS SECTION =====
        status_frame = ttk.LabelFrame(main_frame, text="Upload Status", padding=10)
        status_frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(status_frame, textvariable=self.upload_status, 
                 font=("Arial", 10, "bold"), foreground="blue").pack(anchor=W, pady=(5, 10))
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(status_frame, height=10, width=80, 
                                                   state=DISABLED, font=("Courier", 9))
        self.log_text.pack(fill=BOTH, expand=True)
    
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
            self.upload_status.set("Uploading...")
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
            self.log_message(f"File size: {len(file_content) / (1024*1024):.2f} MB", "info")
            
            response = requests.put(
                upload_url,
                data=file_content,
                headers=headers,
                timeout=30,
                verify=False  # For self-signed certificates
            )
            
            if response.status_code in [200, 201]:
                self.log_message(f"✓ Upload successful! Status: {response.status_code}", "success")
                self.upload_status.set(f"Upload completed - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                messagebox.showinfo("Success", "File uploaded successfully to Artifactory!")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.log_message(f"✗ Upload failed: {error_msg}", "error")
                self.upload_status.set("Upload failed")
                messagebox.showerror("Upload Failed", error_msg)
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            self.log_message(f"✗ {error_msg}", "error")
            self.upload_status.set("Upload failed - Network error")
            messagebox.showerror("Error", error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_message(f"✗ {error_msg}", "error")
            self.upload_status.set("Upload failed")
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
