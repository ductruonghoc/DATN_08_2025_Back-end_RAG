import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import grpc
import json
from dotenv import load_dotenv
import threading
from google.protobuf import empty_pb2, json_format

# Add directory to path for importing generated gRPC modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import generated gRPC modules (assumes they have been compiled)
import pdf_processor_pb2
import pdf_processor_pb2_grpc

# Load environment variables
load_dotenv()

# Constants
MAX_MESSAGE_LENGTH = 100 * 1024 * 1024  # 100MB


class PdfProcessorClient:
    """Client for interacting with the PDF Processor gRPC service."""
    
    def __init__(self, server_address):
        """Initialize the client with server address."""
        # Create gRPC channel with increased message size limit
        channel_options = [
            ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
            ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH)
        ]
        self.channel = grpc.insecure_channel(server_address, options=channel_options)
        self.stub = pdf_processor_pb2_grpc.PdfProcessorStub(self.channel)
    
    def check_health(self):
        """Check server health."""
        try:
            response = self.stub.HealthCheck(empty_pb2.Empty())
            return response.status
        except grpc.RpcError as e:
            return f"Error: {e.details() if hasattr(e, 'details') else str(e)}"
    
    def process_pdf(self, file_path):
        """Process a PDF file and return structured data."""
        try:
            # Read PDF file
            with open(file_path, 'rb') as file:
                pdf_data = file.read()
            
            # Create request
            filename = os.path.basename(file_path)
            request = pdf_processor_pb2.PdfRequest(
                pdf_data=pdf_data,
                filename=filename
            )
            
            # Send request
            response = self.stub.ProcessPdf(request)
            
            if response.success:
                # Convert Protobuf Struct to Python dict
                result_dict = json_format.MessageToDict(
                    response.data,
                )
                return True, response.message, result_dict
            else:
                return False, response.message, None
                
        except grpc.RpcError as e:
            error_message = f"RPC Error: {e.details() if hasattr(e, 'details') else str(e)}"
            return False, error_message, None
        except Exception as e:
            error_message = f"Error: {str(e)}"
            return False, error_message, None
    
    def close(self):
        """Close the gRPC channel."""
        self.channel.close()


class PdfProcessorApp:
    """Tkinter application for PDF processing."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("PDF Processor Client")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Server connection
        self.server_address = tk.StringVar(value="localhost:50051")
        self.client = None
        
        # Create UI
        self.create_widgets()
        
        # Connect to server on startup
        self.connect_to_server()
    
    def create_widgets(self):
        """Create the UI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Server connection frame
        server_frame = ttk.LabelFrame(main_frame, text="Server Connection", padding="10")
        server_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(server_frame, text="Server Address:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(server_frame, textvariable=self.server_address, width=30).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.connect_button = ttk.Button(server_frame, text="Connect", command=self.connect_to_server)
        self.connect_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.status_label = ttk.Label(server_frame, text="Status: Not connected")
        self.status_label.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="PDF Selection", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_path = tk.StringVar()
        ttk.Label(file_frame, text="PDF File:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
        
        browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_button.grid(row=0, column=2, padx=5, pady=5)
        
        process_button = ttk.Button(file_frame, text="Process PDF", command=self.process_pdf)
        process_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=15, pady=5)
        
        # Results frame with notebook
        results_frame = ttk.LabelFrame(main_frame, text="Processing Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for results
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Raw JSON tab
        self.json_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.json_tab, text="Raw JSON")
        
        self.json_text = scrolledtext.ScrolledText(self.json_tab, wrap=tk.WORD)
        self.json_text.pack(fill=tk.BOTH, expand=True)
        
        # Formatted view tab
        self.formatted_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.formatted_tab, text="Formatted View")
        
        # Create a treeview for structured data
        self.tree_frame = ttk.Frame(self.formatted_tab)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(self.tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree_scroll_x = ttk.Scrollbar(self.tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.tree = ttk.Treeview(self.tree_frame, yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # Configure treeview
        self.tree["columns"] = ("value")
        self.tree.column("#0", width=250, minwidth=150)
        self.tree.column("value", width=400, minwidth=200)
        
        self.tree.heading("#0", text="Key")
        self.tree.heading("value", text="Value")
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def connect_to_server(self):
        """Connect to the gRPC server."""
        try:
            address = self.server_address.get()
            self.status_label.config(text="Status: Connecting...")
            self.root.update()
            
            # Create client
            self.client = PdfProcessorClient(address)
            
            # Check server health
            def check_health_thread():
                status = self.client.check_health()
                
                # Update UI from main thread
                self.root.after(0, lambda: self.update_connection_status(status))
            
            # Run in a separate thread to avoid blocking UI
            threading.Thread(target=check_health_thread, daemon=True).start()
            
        except Exception as e:
            self.status_label.config(text=f"Status: Error - {str(e)}")
            messagebox.showerror("Connection Error", str(e))
    
    def update_connection_status(self, status):
        """Update the connection status label."""
        if status == "healthy":
            self.status_label.config(text="Status: Connected")
            self.connect_button.config(text="Reconnect")
        else:
            self.status_label.config(text=f"Status: Error - {status}")
            self.client = None
    
    def browse_file(self):
        """Open file dialog to select a PDF file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if file_path:
            self.file_path.set(file_path)
    
    def process_pdf(self):
        """Process the selected PDF file."""
        if not self.client:
            messagebox.showerror("Error", "Not connected to server. Please connect first.")
            return
        
        file_path = self.file_path.get()
        if not file_path:
            messagebox.showerror("Error", "Please select a PDF file.")
            return
        
        if not os.path.isfile(file_path):
            messagebox.showerror("Error", "Selected file does not exist.")
            return
        
        # Clear previous results
        self.json_text.delete(1.0, tk.END)
        self.tree.delete(*self.tree.get_children())
        
        # Update status
        self.status_bar.config(text=f"Processing: {os.path.basename(file_path)}")
        self.progress_var.set(10)
        self.root.update()
        
        # Process PDF in a separate thread
        def process_thread():
            try:
                # Update progress
                self.root.after(0, lambda: self.progress_var.set(30))
                
                # Process the PDF
                success, message, result = self.client.process_pdf(file_path)
                
                # Update progress
                self.root.after(0, lambda: self.progress_var.set(90))
                
                # Update UI from main thread
                self.root.after(0, lambda: self.update_results(success, message, result))
                
            except Exception as e:
                self.root.after(0, lambda: self.handle_processing_error(str(e)))
        
        # Run in a separate thread to avoid blocking UI
        threading.Thread(target=process_thread, daemon=True).start()
    
    def update_results(self, success, message, result):
        """Update the UI with processing results."""
        if success:
            # Format and display JSON
            json_str = json.dumps(result, indent=2)
            self.json_text.insert(tk.END, json_str)
            
            # Populate tree view
            self.populate_tree("", result)
            
            # Update status
            self.status_bar.config(text=message)
            messagebox.showinfo("Success", message)
            
        else:
            self.status_bar.config(text=f"Error: {message}")
            messagebox.showerror("Processing Error", message)
        
        # Complete progress
        self.progress_var.set(100)
    
    def handle_processing_error(self, error_message):
        """Handle processing errors."""
        self.status_bar.config(text=f"Error: {error_message}")
        self.progress_var.set(0)
        messagebox.showerror("Error", error_message)
    
    def populate_tree(self, parent, data):
        """Recursively populate treeview with structured data."""
        if isinstance(data, dict):
            for key, value in data.items():
                node_id = self.tree.insert(parent, "end", text=key, values=("" if isinstance(value, (dict, list)) else str(value)))
                
                if isinstance(value, (dict, list)):
                    self.populate_tree(node_id, value)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                node_id = self.tree.insert(parent, "end", text=f"[{i}]", values=("" if isinstance(item, (dict, list)) else str(item)))
                
                if isinstance(item, (dict, list)):
                    self.populate_tree(node_id, item)


if __name__ == "__main__":
    root = tk.Tk()
    app = PdfProcessorApp(root)
    root.mainloop()