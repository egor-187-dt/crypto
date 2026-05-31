# NEW FILE for Sprint 5
"""
Export formatters for audit logs in JSON, CSV, and PDF formats.
Implements requirements EXP-1, EXP-2, EXP-3, EXP-4.
"""

import json
import csv
import io
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import base64


@dataclass
class ExportMetadata:
    """Metadata for export operations per EXP-2."""
    timestamp: str
    exporter: str
    start_date: Optional[str]
    end_date: Optional[str]
    total_entries: int
    format: str
    signature_included: bool


class LogFormatter:
    """
    Formats audit logs for export in various formats.
    Supports JSON, CSV, and PDF outputs.
    """

    def __init__(self, signer=None):
        """
        Initialize formatter.

        Args:
            signer: Optional signer for signing exports per EXP-2
        """
        self.signer = signer

    def export_to_json(self, entries: List[Dict[str, Any]],
                       metadata: ExportMetadata,
                       include_signatures: bool = True) -> str:
        """
        Export logs to signed JSON format per EXP-1, EXP-2.

        Args:
            entries: List of log entries
            metadata: Export metadata
            include_signatures: Whether to include signatures

        Returns:
            JSON string
        """
        export_data = {
            'metadata': {
                'timestamp': metadata.timestamp,
                'exporter': metadata.exporter,
                'start_date': metadata.start_date,
                'end_date': metadata.end_date,
                'total_entries': metadata.total_entries,
                'format': metadata.format,
                'signature_included': include_signatures
            },
            'entries': []
        }

        for entry in entries:
            entry_copy = entry.copy()

            # Include signature if requested per EXP-2
            if include_signatures and 'signature' in entry_copy:
                # Keep signature as hex string
                pass
            elif 'signature' in entry_copy:
                del entry_copy['signature']

            export_data['entries'].append(entry_copy)

        # Sign the entire export if signer available per EXP-2
        if self.signer and include_signatures:
            export_json = json.dumps(export_data, sort_keys=True)
            signature = self.signer.sign(export_json.encode())
            export_data['export_signature'] = signature.hex()

            # Include public key for verification per EXP-2
            if hasattr(self.signer, 'get_public_key_bytes'):
                pub_key = self.signer.get_public_key_bytes()
                if pub_key:
                    export_data['public_key'] = base64.b64encode(pub_key).decode('ascii')

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    def export_to_csv(self, entries: List[Dict[str, Any]]) -> str:
        """
        Export logs to CSV format per EXP-1.

        Args:
            entries: List of log entries

        Returns:
            CSV string
        """
        output = io.StringIO()

        if not entries:
            return ""

        # Define CSV columns
        fieldnames = ['sequence_number', 'timestamp', 'event_type', 'severity',
                      'user_id', 'source', 'details']

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            row = {
                'sequence_number': entry.get('sequence_number', ''),
                'timestamp': entry.get('timestamp', ''),
                'event_type': entry.get('event_type', ''),
                'severity': entry.get('severity', ''),
                'user_id': entry.get('user_id', ''),
                'source': entry.get('source', ''),
                'details': json.dumps(entry.get('details', {}))
            }
            writer.writerow(row)

        return output.getvalue()

    def export_to_pdf(self, entries: List[Dict[str, Any]],
                      metadata: ExportMetadata) -> bytes:
        """
        Export logs to PDF format per EXP-1.

        Note: This is a stub implementation. Full PDF generation
        would require reportlab or similar library.

        Args:
            entries: List of log entries
            metadata: Export metadata

        Returns:
            PDF bytes (stub)
        """
        # Stub implementation as per TZ
        # Full implementation would use reportlab to generate proper PDF

        pdf_content = f"""
        CRYPTOSAFE MANAGER - AUDIT LOG EXPORT
        =====================================

        Export Date: {metadata.timestamp}
        Exported By: {metadata.exporter}
        Date Range: {metadata.start_date or 'All'} to {metadata.end_date or 'All'}
        Total Entries: {metadata.total_entries}

        LOG ENTRIES:
        -------------

        """

        for entry in entries[:100]:  # Limit to first 100 in stub
            pdf_content += f"""
        [{entry.get('timestamp', 'N/A')}] {entry.get('severity', 'INFO')}
        Event: {entry.get('event_type', 'UNKNOWN')}
        User: {entry.get('user_id', 'anonymous')}
        Source: {entry.get('source', 'unknown')}
        Details: {json.dumps(entry.get('details', {}), indent=2)}
        ----------------------------------------
        """

        # Return as bytes (stub)
        return pdf_content.encode('utf-8')

    def export_batch(self, entries_by_range: Dict[str, List[Dict[str, Any]]],
                     format: str = 'json',
                     include_signatures: bool = True) -> Dict[str, str]:
        """
        Export multiple batches of logs per EXP-4.

        Args:
            entries_by_range: Dict mapping range names to entry lists
            format: Export format ('json', 'csv', 'pdf')
            include_signatures: Whether to include signatures

        Returns:
            Dict mapping range names to exported content
        """
        results = {}

        for range_name, entries in entries_by_range.items():
            metadata = ExportMetadata(
                timestamp=datetime.now(timezone.utc).isoformat(),
                exporter='CryptoSafe Manager',
                start_date=None,
                end_date=None,
                total_entries=len(entries),
                format=format,
                signature_included=include_signatures
            )

            if format == 'json':
                results[range_name] = self.export_to_json(entries, metadata, include_signatures)
            elif format == 'csv':
                results[range_name] = self.export_to_csv(entries)
            elif format == 'pdf':
                results[range_name] = self.export_to_pdf(entries, metadata).decode('utf-8', errors='ignore')

        return results