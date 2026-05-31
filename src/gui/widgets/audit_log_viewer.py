# EXTENDED for Sprint 5 - Audit trail viewer with filtering, search, and verification status
"""
Audit log viewer widget with advanced filtering and integrity display.
Implements requirements GUI-1, GUI-2, GUI-3, GUI-4.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List, Optional

# NEW for Sprint 5
from src.core.audit.log_verifier import VerificationStatus


class AuditLogViewer(ttk.Frame):
    """
    Audit log viewer with filtering, search, and verification display.
    Extended in Sprint 5 with integrity visualization and statistics.
    """

    def __init__(self, parent, audit_logger, log_verifier, event_system):
        """
        Initialize audit log viewer.

        Args:
            parent: Parent widget
            audit_logger: AuditLogger instance
            log_verifier: LogVerifier instance
            event_system: Event bus for notifications
        """
        super().__init__(parent)
        self.audit_logger = audit_logger
        self.log_verifier = log_verifier
        self.events = event_system
        self.current_page = 0
        self.page_size = 50  # GUI-1 pagination
        self.current_filters = {}

        self._setup_ui()
        self._bind_events()
        self.load_entries()

    def _setup_ui(self):
        """Setup the audit log viewer UI per GUI-1."""
        # Filter frame
        self.filter_frame = ttk.LabelFrame(self, text="Filters", padding=5)
        self.filter_frame.pack(fill=tk.X, padx=5, pady=5)

        # Filter controls per GUI-1
        ttk.Label(self.filter_frame, text="Event Type:").grid(row=0, column=0, padx=5)
        self.event_type_var = tk.StringVar()
        self.event_type_combo = ttk.Combobox(self.filter_frame, textvariable=self.event_type_var,
                                             values=['All', 'AUTH_LOGIN', 'AUTH_LOGOUT',
                                                     'VAULT_CREATE', 'VAULT_UPDATE', 'VAULT_DELETE',
                                                     'CLIPBOARD_COPY', 'CLIPBOARD_CLEAR',
                                                     'SYSTEM_LOCK', 'SYSTEM_UNLOCK'])
        self.event_type_combo.grid(row=0, column=1, padx=5)

        ttk.Label(self.filter_frame, text="Severity:").grid(row=0, column=2, padx=5)
        self.severity_var = tk.StringVar()
        self.severity_combo = ttk.Combobox(self.filter_frame, textvariable=self.severity_var,
                                           values=['All', 'INFO', 'WARN', 'ERROR', 'CRITICAL'])
        self.severity_combo.grid(row=0, column=3, padx=5)

        ttk.Label(self.filter_frame, text="Date From:").grid(row=1, column=0, padx=5, pady=5)
        self.date_from_var = tk.StringVar()
        self.date_from_entry = ttk.Entry(self.filter_frame, textvariable=self.date_from_var, width=20)
        self.date_from_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self.filter_frame, text="Date To:").grid(row=1, column=2, padx=5, pady=5)
        self.date_to_var = tk.StringVar()
        self.date_to_entry = ttk.Entry(self.filter_frame, textvariable=self.date_to_var, width=20)
        self.date_to_entry.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(self.filter_frame, text="Search:").grid(row=1, column=4, padx=5, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.filter_frame, textvariable=self.search_var, width=20)
        self.search_entry.grid(row=1, column=5, padx=5, pady=5)

        self.filter_btn = ttk.Button(self.filter_frame, text="Apply Filters", command=self.apply_filters)
        self.filter_btn.grid(row=1, column=6, padx=5, pady=5)

        self.reset_btn = ttk.Button(self.filter_frame, text="Reset", command=self.reset_filters)
        self.reset_btn.grid(row=1, column=7, padx=5, pady=5)

        # Verification status indicator per GUI-2
        self.status_frame = ttk.Frame(self.filter_frame)
        self.status_frame.grid(row=0, column=8, rowspan=2, padx=10)

        self.verify_status_label = ttk.Label(self.status_frame, text="🔍 Integrity: Pending", font=('Arial', 10, 'bold'))
        self.verify_status_label.pack()

        self.verify_btn = ttk.Button(self.status_frame, text="Verify Now", command=self.manual_verify)
        self.verify_btn.pack(pady=5)

        # Tree view for log entries per GUI-1
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add scrollbars
        self.scroll_y = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL)
        self.scroll_x = ttk.Scrollbar(self.tree_frame, orient=tk.HORIZONTAL)

        # Create treeview with sortable columns
        self.tree = ttk.Treeview(self.tree_frame,
                                 columns=('seq', 'timestamp', 'event_type', 'severity', 'user', 'source', 'status'),
                                 show='headings',
                                 yscrollcommand=self.scroll_y.set,
                                 xscrollcommand=self.scroll_x.set)

        self.scroll_y.config(command=self.tree.yview)
        self.scroll_x.config(command=self.tree.xview)

        # Define columns per GUI-1
        self.tree.heading('seq', text='Seq #', command=lambda: self._sort_column('seq'))
        self.tree.heading('timestamp', text='Timestamp', command=lambda: self._sort_column('timestamp'))
        self.tree.heading('event_type', text='Event Type', command=lambda: self._sort_column('event_type'))
        self.tree.heading('severity', text='Severity', command=lambda: self._sort_column('severity'))
        self.tree.heading('user', text='User', command=lambda: self._sort_column('user'))
        self.tree.heading('source', text='Source', command=lambda: self._sort_column('source'))
        self.tree.heading('status', text='Verification', command=lambda: self._sort_column('status'))

        # Configure column widths
        self.tree.column('seq', width=60)
        self.tree.column('timestamp', width=180)
        self.tree.column('event_type', width=150)
        self.tree.column('severity', width=80)
        self.tree.column('user', width=120)
        self.tree.column('source', width=100)
        self.tree.column('status', width=100)

        # Pack treeview
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.scroll_y.grid(row=0, column=1, sticky='ns')
        self.scroll_x.grid(row=1, column=0, sticky='ew')

        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        # Bind selection event for details panel per GUI-2
        self.tree.bind('<<TreeviewSelect>>', self._on_entry_selected)
        self.tree.bind('<Button-3>', self._show_context_menu)  # Right-click per GUI-4

        # Details panel per GUI-2
        self.details_frame = ttk.LabelFrame(self, text="Entry Details", padding=5)
        self.details_frame.pack(fill=tk.X, padx=5, pady=5)

        self.details_text = tk.Text(self.details_frame, height=8, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True)

        # Pagination controls per GUI-1
        self.pagination_frame = ttk.Frame(self)
        self.pagination_frame.pack(fill=tk.X, padx=5, pady=5)

        self.prev_btn = ttk.Button(self.pagination_frame, text="◀ Previous", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.page_label = ttk.Label(self.pagination_frame, text="Page 1")
        self.page_label.pack(side=tk.LEFT, padx=10)

        self.next_btn = ttk.Button(self.pagination_frame, text="Next ▶", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.status_bar = ttk.Label(self.pagination_frame, text="", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

        # Statistics button per GUI-3
        self.stats_btn = ttk.Button(self.pagination_frame, text="📊 Statistics", command=self.show_statistics)
        self.stats_btn.pack(side=tk.RIGHT, padx=5)

        # Export buttons per EXP-1
        self.export_json_btn = ttk.Button(self.pagination_frame, text="Export JSON",
                                          command=lambda: self.export_logs('json'))
        self.export_json_btn.pack(side=tk.RIGHT, padx=5)

        self.export_csv_btn = ttk.Button(self.pagination_frame, text="Export CSV",
                                         command=lambda: self.export_logs('csv'))
        self.export_csv_btn.pack(side=tk.RIGHT, padx=5)

        self.export_pdf_btn = ttk.Button(self.pagination_frame, text="Export PDF",
                                         command=lambda: self.export_logs('pdf'))
        self.export_pdf_btn.pack(side=tk.RIGHT, padx=5)

    def _bind_events(self):
        """Bind to event system for real-time updates."""
        self.events.subscribe('IntegrityStatusUpdate', self._on_integrity_update)
        self.events.subscribe('SecurityEvent', self._on_security_event)

    def _sort_column(self, col):
        """Sort treeview by column."""
        # Get current items
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]

        # Sort
        items.sort(key=lambda x: x[0])

        # Reorder
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)

    def _on_entry_selected(self, event):
        """Show detailed entry information per GUI-2."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        entry_data = self.tree.item(item, 'tags')
        if entry_data and len(entry_data) > 0:
            self._display_entry_details(entry_data[0])

    def _display_entry_details(self, entry: Dict[str, Any]):
        """Display entry details with JSON formatting per GUI-2."""
        self.details_text.delete(1.0, tk.END)

        # Format JSON for readability
        details = {
            'timestamp': entry.get('timestamp'),
            'event_type': entry.get('event_type'),
            'severity': entry.get('severity'),
            'user_id': entry.get('user_id'),
            'source': entry.get('source'),
            'sequence_number': entry.get('sequence_number'),
            'details': entry.get('details', {}),
            'verification_status': entry.get('verification_status', 'unknown')
        }

        formatted = json.dumps(details, indent=2, ensure_ascii=False)
        self.details_text.insert(1.0, formatted)

        # Highlight verification status per GUI-2
        status = entry.get('verification_status', 'pending')
        if status == 'valid':
            self.details_text.tag_add('valid', '1.0', tk.END)
            self.details_text.tag_config('valid', foreground='green')
        elif status in ['invalid', 'tampered']:
            self.details_text.tag_add('invalid', '1.0', tk.END)
            self.details_text.tag_config('invalid', foreground='red')

    def _show_context_menu(self, event):
        """Show context menu per GUI-4."""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        self.tree.selection_set(item)

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="🔍 View Details", command=lambda: self._on_entry_selected(None))
        menu.add_separator()
        menu.add_command(label="📋 Copy Event Type", command=lambda: self._copy_to_clipboard('event_type'))
        menu.add_command(label="📋 Copy Timestamp", command=lambda: self._copy_to_clipboard('timestamp'))
        menu.add_separator()
        menu.add_command(label="🔗 Related Vault Entry", command=self._open_related_entry)
        menu.add_command(label="⚠️ Report Suspicious", command=self._report_suspicious)

        menu.post(event.x_root, event.y_root)

    def _copy_to_clipboard(self, field: str):
        """Copy specific field to clipboard."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.tree.item(item, 'values')

        field_index = {
            'event_type': 2,
            'timestamp': 1
        }.get(field)

        if field_index and len(values) > field_index:
            self.clipboard_clear()
            self.clipboard_append(str(values[field_index]))

    def _open_related_entry(self):
        """Open related vault entry per GUI-4."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if tags and len(tags) > 0:
            entry = tags[0]
            entry_id = entry.get('details', {}).get('entry_id')
            if entry_id:
                self.events.publish('NavigateToEntry', {'entry_id': entry_id})

    def _report_suspicious(self):
        """Report suspicious entry for investigation."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.tree.item(item, 'tags')

        if messagebox.askyesno("Report Suspicious", "Mark this entry as suspicious for review?"):
            self.events.publish('SuspiciousActivityReported', {
                'entry': tags[0] if tags else None,
                'reported_by': 'user',
                'timestamp': datetime.now().isoformat()
            })
            messagebox.showinfo("Reported", "Suspicious activity has been reported.")

    def load_entries(self):
        """Load log entries with current filters and pagination."""
        # Build filters
        filters = {}

        if self.event_type_var.get() and self.event_type_var.get() != 'All':
            filters['event_type'] = self.event_type_var.get()

        if self.severity_var.get() and self.severity_var.get() != 'All':
            filters['severity'] = self.severity_var.get()

        if self.date_from_var.get():
            filters['start_date'] = self.date_from_var.get()

        if self.date_to_var.get():
            filters['end_date'] = self.date_to_var.get()

        # Load entries
        offset = self.current_page * self.page_size
        entries = self.audit_logger.get_entries(
            limit=self.page_size,
            offset=offset,
            event_type=filters.get('event_type'),
            severity=filters.get('severity'),
            start_date=filters.get('start_date'),
            end_date=filters.get('end_date')
        )

        total = self.audit_logger.get_total_count(
            event_type=filters.get('event_type'),
            severity=filters.get('severity')
        )

        # Update pagination display
        total_pages = (total + self.page_size - 1) // self.page_size
        self.page_label.config(text=f"Page {self.current_page + 1} of {max(1, total_pages)}")

        self.status_bar.config(text=f"Showing {len(entries)} of {total} entries")

        # Apply search filter if present
        search_term = self.search_var.get().lower()
        if search_term:
            entries = [e for e in entries if self._matches_search(e, search_term)]
            self.status_bar.config(text=f"Showing {len(entries)} of {total} entries (filtered)")

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insert entries
        for entry in entries:
            # Determine verification status display
            status = entry.get('verification_status', 'pending')
            status_icon = {
                'valid': '✅',
                'invalid': '❌',
                'pending': '⏳',
                'tampered': '⚠️'
            }.get(status, '❓')

            self.tree.insert('', tk.END, values=(
                entry.get('sequence_number', ''),
                entry.get('timestamp', '')[:19],
                entry.get('event_type', ''),
                entry.get('severity', ''),
                entry.get('user_id', ''),
                entry.get('source', ''),
                f"{status_icon} {status}"
            ), tags=(entry,))

    def _matches_search(self, entry: Dict[str, Any], search_term: str) -> bool:
        """Check if entry matches search term."""
        if search_term in str(entry.get('event_type', '')).lower():
            return True
        if search_term in str(entry.get('user_id', '')).lower():
            return True
        if search_term in str(entry.get('details', {})).lower():
            return True
        return False

    def apply_filters(self):
        """Apply current filters and reload."""
        self.current_page = 0
        self.load_entries()

    def reset_filters(self):
        """Reset all filters."""
        self.event_type_var.set('All')
        self.severity_var.set('All')
        self.date_from_var.set('')
        self.date_to_var.set('')
        self.search_var.set('')
        self.current_page = 0
        self.load_entries()

    def prev_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_entries()

    def next_page(self):
        """Go to next page."""
        self.current_page += 1
        self.load_entries()

    def manual_verify(self):
        """Manually trigger full verification per VER-3."""
        self.verify_status_label.config(text="🔍 Verifying...", foreground='orange')
        self.status_bar.config(text="Running integrity verification...")

        # Run verification in background
        self.after(100, self._run_verification)

    def _run_verification(self):
        """Run verification in background thread."""
        import threading

        def verify():
            result = self.log_verifier.verify_integrity(full_scan=True)
            self.after(0, lambda: self._on_verification_complete(result))

        threading.Thread(target=verify, daemon=True).start()

    def _on_verification_complete(self, result):
        """Handle verification completion."""
        if result.verified:
            self.verify_status_label.config(text="✅ Integrity: Verified", foreground='green')
            self.status_bar.config(text=f"Verification passed - {result.valid_entries}/{result.total_entries} valid")
            messagebox.showinfo("Verification Complete",
                                f"All {result.total_entries} entries verified successfully.")
        else:
            self.verify_status_label.config(text="❌ Integrity: COMPROMISED", foreground='red')
            self.status_bar.config(text=f"⚠️ Verification failed - {len(result.invalid_entries)} invalid entries")

            messagebox.showerror("Verification Failed",
                                 f"Found {len(result.invalid_entries)} invalid entries and "
                                 f"{len(result.chain_breaks)} chain breaks!\n\n"
                                 f"Check details panel for more information.")

        # Reload to show updated statuses
        self.load_entries()

    def _on_integrity_update(self, event_data):
        """Handle periodic integrity status update per VER-2."""
        if event_data.get('verified'):
            self.verify_status_label.config(text="✅ Integrity: Verified", foreground='green')
        else:
            self.verify_status_label.config(text="⚠️ Integrity: Issues Detected", foreground='orange')

    def _on_security_event(self, event_data):
        """Handle security events and show notifications."""
        if event_data.get('event_type') == 'LOG_TAMPERING_DETECTED':
            self.verify_status_label.config(text="🚨 TAMPERING DETECTED!", foreground='red')
            self.status_bar.config(text="⚠️ CRITICAL: Log tampering detected!")

    def show_statistics(self):
        """Show statistics dashboard per GUI-3."""
        stats_window = tk.Toplevel(self)
        stats_window.title("Audit Statistics")
        stats_window.geometry("600x400")

        # Get statistics from verifier
        report = self.log_verifier.get_verification_report()

        # Create notebook for tabs
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Overview tab
        overview_frame = ttk.Frame(notebook)
        notebook.add(overview_frame, text="Overview")

        stats_text = tk.Text(overview_frame, wrap=tk.WORD)
        stats_text.pack(fill=tk.BOTH, expand=True)

        stats_text.insert(tk.END, "AUDIT LOG STATISTICS\n")
        stats_text.insert(tk.END, "=" * 50 + "\n\n")
        stats_text.insert(tk.END, f"Status: {report.get('status', 'Unknown')}\n")
        stats_text.insert(tk.END, f"Total Entries Checked: {report.get('total_entries_checked', 0)}\n")
        stats_text.insert(tk.END, f"Valid Entries: {report.get('valid_entries', 0)}\n")
        stats_text.insert(tk.END, f"Invalid Entries: {report.get('invalid_entries_count', 0)}\n")
        stats_text.insert(tk.END, f"Chain Breaks: {report.get('chain_breaks_count', 0)}\n")
        stats_text.insert(tk.END, f"Verification Time: {report.get('verification_time_ms', 0):.2f} ms\n")
        stats_text.insert(tk.END, f"Last Check: {report.get('timestamp', 'N/A')}\n")

        # Event frequency tab per GUI-3
        freq_frame = ttk.Frame(notebook)
        notebook.add(freq_frame, text="Event Frequency")

        # Get event counts
        event_counts = self._get_event_counts()

        freq_text = tk.Text(freq_frame, wrap=tk.WORD)
        freq_text.pack(fill=tk.BOTH, expand=True)

        freq_text.insert(tk.END, "EVENT FREQUENCY\n")
        freq_text.insert(tk.END, "=" * 50 + "\n\n")

        for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            freq_text.insert(tk.END, f"{event_type}: {count}\n")

        stats_text.config(state=tk.DISABLED)
        freq_text.config(state=tk.DISABLED)

    def _get_event_counts(self) -> Dict[str, int]:
        """Get event type counts for statistics."""
        counts = {}
        entries = self.audit_logger.get_entries(limit=10000)

        for entry in entries:
            event_type = entry.get('event_type', 'UNKNOWN')
            counts[event_type] = counts.get(event_type, 0) + 1

        return counts

    def export_logs(self, format_type: str):
        """Export logs in specified format per EXP-1."""
        # Get current view (could be filtered)
        entries = []
        for item in self.tree.get_children():
            tags = self.tree.item(item, 'tags')
            if tags and len(tags) > 0:
                entries.append(tags[0])

        if not entries:
            messagebox.showwarning("No Data", "No entries to export.")
            return

        # Ask for confirmation per EXP-3
        if not messagebox.askyesno("Confirm Export",
                                   f"Export {len(entries)} entries to {format_type.upper()}?\n\n"
                                   "This operation will be logged in audit trail."):
            return

        # Request master password confirmation per EXP-3
        from src.gui.password_dialog import PasswordDialog
        password_dialog = PasswordDialog(self)
        if not password_dialog.result:
            messagebox.showwarning("Export Cancelled", "Master password required for export.")
            return

        # Perform export
        from src.core.audit.log_formatters import LogFormatter, ExportMetadata

        formatter = LogFormatter()
        metadata = ExportMetadata(
            timestamp=datetime.now().isoformat(),
            exporter='CryptoSafe Manager',
            start_date=self.date_from_var.get() or None,
            end_date=self.date_to_var.get() or None,
            total_entries=len(entries),
            format=format_type,
            signature_included=True
        )

        try:
            if format_type == 'json':
                content = formatter.export_to_json(entries, metadata, include_signatures=True)
                ext = 'json'
            elif format_type == 'csv':
                content = formatter.export_to_csv(entries)
                ext = 'csv'
            elif format_type == 'pdf':
                content = formatter.export_to_pdf(entries, metadata)
                ext = 'pdf'
            else:
                return

            # Save to file
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=f".{ext}",
                filetypes=[(f"{format_type.upper()} files", f"*.{ext}"), ("All files", "*.*")]
            )

            if filename:
                if isinstance(content, str):
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    with open(filename, 'wb') as f:
                        f.write(content)

                messagebox.showinfo("Export Complete", f"Exported {len(entries)} entries to {filename}")

                # Log the export operation per EXP-3
                self.audit_logger.log_event(
                    event_type='EXPORT_LOGS',
                    severity='INFO',
                    source='audit_viewer',
                    details={
                        'format': format_type,
                        'entry_count': len(entries),
                        'filename': filename
                    }
                )

        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export: {str(e)}")