from dataclasses import fields
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fe_cr.models import ElectronicInvoice, InvoiceLine, InvoiceSummary


def test_invoice_line_codigo_optional_default_none():
    line_fields = {f.name: f for f in fields(InvoiceLine)}
    assert line_fields["codigo"].default is None


def test_invoice_summary_tipo_cambio_optional_default_none():
    summary_fields = {f.name: f for f in fields(InvoiceSummary)}
    assert summary_fields["tipo_cambio"].default is None


def test_electronic_invoice_optional_defaults_align_with_odoo_structure():
    invoice_fields = {f.name: f for f in fields(ElectronicInvoice)}
    assert invoice_fields["receptor"].default is None
    assert invoice_fields["plazo_credito"].default is None
    assert invoice_fields["medios_pago"].default_factory() == tuple()
