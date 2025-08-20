import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from app.models import LocationList



def render_transaction_pdf_page(pdf, transaction):
    # Fetch the location and other required data (like in the original route)
    location = LocationList.query.filter_by(location=transaction.location).first() if transaction and transaction.location else None

    # Define page size and layout
    width, height = A4

    # Add the title (centered)
    pdf.setFont("Helvetica-Bold", 16)
    title = "Öffentliche 50t Waage"
    title_width = pdf.stringWidth(title, "Helvetica-Bold", 16)
    pdf.drawString((width - title_width) / 2, height - 40, title or "")

    # Horizontal divider line (full width)
    pdf.setLineWidth(1)
    pdf.line(50, height - 50, width - 50, height - 50)

    # Add company info (centered)
    pdf.setFont("Helvetica", 10)
    company_info = f"{(location.entity or '')} | {(location.street_no or '')} | {(location.zip_place or '')}" if location else ""
    company_info_width = pdf.stringWidth(company_info, "Helvetica", 10)
    pdf.drawString((width - company_info_width) / 2, height - 70, company_info)

    # Add contact info (centered)
    contact_info = (
        f"{(location.phone or '')} | {(location.email or '')} | {(location.url or '')}"
        if location else ""
    )        
    contact_info_width = pdf.stringWidth(contact_info, "Helvetica", 10)
    pdf.drawString((width - contact_info_width) / 2, height - 85, contact_info or "")

    # Add vertical space (1 rem, ~10px, 1 rem = 10px)
    pdf.translate(0, -20)

    # Data Section (slip ID)
    pdf.setFont("Helvetica-Bold", 16)
    # Left-aligned "Belegnr"
    pdf.drawString(50, height - 100, f"Beleg-Nr: {transaction.id or 'N/A'}")

    # Add vertical space (1 rem, ~10px, 1 rem = 10px)
    pdf.translate(0, -10)

    # Data Section (Kunde, Produkt, Spedition/Behälter)
    pdf.setFont("Helvetica-Bold", 10)
    # Left-aligned "Kunde"
    pdf.drawString(50, height - 110, "Kunde")
    

    customer_text = (transaction.customer or "")[:70]
    customer_text_wrapped = textwrap.wrap(customer_text, width=35)
    ypos = height - 125
    line_height = 12
    customer_text_obj = pdf.beginText(50, ypos)

    for line in customer_text_wrapped:
        customer_text_obj.textLine(line)
        ypos -= line_height  # Adjust y for next line

    pdf.setFont("Helvetica", 10)
    pdf.drawText(customer_text_obj)     


    # Data Section (Auftragsnr/Projekt)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, height - 155, "AuftrNr/Proj")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, height - 175, transaction.order_number or "")

    # Right-aligned "Produkt"
    pdf.setFont("Helvetica-Bold", 10)
    product_label_x = width - 150
    pdf.drawString(product_label_x, height - 110, "Produkt")

    # Right-aligned product info (wrapped)
    pdf.setFont("Helvetica", 10)
    sku = transaction.sku or ''
    category = transaction.material_category or ''
    raw_label = f"{sku} {category}".strip()[:46]  # Max 46 characters

    wrapped_lines = textwrap.wrap(raw_label, width=23)  # Max 23 per line

    ypos = height - 125
    line_height = 12
    for line in wrapped_lines:
        pdf.drawString(product_label_x, ypos, line)
        ypos -= line_height


    # Right-aligned "Spedition/Behälter"
    pdf.setFont("Helvetica-Bold", 10)
    container_label_x = width - 150
    pdf.drawString(container_label_x, height - 155, "Spedition/Behälter")
    
    # Right-aligned container and carrier info

    # Build the label string
    lines = []

    if transaction.container_type:
        lines.append(transaction.container_type)

    if transaction.carrier:
        lines.append(transaction.carrier)

    # Join the lines with a newline (only if both exist)
    label_text = "\n".join(lines)

    # Draw the string (multi-line handling)
    text_object = pdf.beginText(container_label_x, height - 175)
    for line in label_text.splitlines():
        text_object.textLine(line)
    pdf.setFont("Helvetica", 10)
    pdf.drawText(text_object)


    # Add vertical space (3 rem, ~30px, 1 rem = 10px)
    pdf.translate(0, -30)

    # New Segment: Datum and Zeit
    # Left column "Datum"
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(71, height - 175, "Datum")
    
    # Left-aligned first timestamp (dd.mm.yy format)
    pdf.setFont("Helvetica", 10)
    first_date = transaction.first_timestamp.strftime('%d.%m.%y') if transaction.first_timestamp else 'N/A'
    pdf.drawString(50, height - 195, f"W1: {first_date}" or "")

    # Right column "Zeit"
    pdf.setFont("Helvetica-Bold", 10)
    time_label_x = 50 + 80  # Adjusted to be 1 tab further right
    pdf.drawString(time_label_x, height - 175, "Zeit")
    
    # Left-aligned first timestamp time (hh:mm format)
    pdf.setFont("Helvetica", 10)
    first_time = transaction.first_timestamp.strftime('%H:%M') if transaction.first_timestamp else 'N/A'
    pdf.drawString(time_label_x, height - 195, first_time or "")

    # Next line: second timestamp (Datum)
    pdf.setFont("Helvetica", 10)
    second_date = transaction.second_timestamp.strftime('%d.%m.%y') if transaction.second_timestamp else 'N/A'
    pdf.drawString(50, height - 215, f"W2: {second_date}" or "")

    # Next line: second timestamp (Zeit)
    second_time = transaction.second_timestamp.strftime('%H:%M') if transaction.second_timestamp else 'N/A'
    pdf.drawString(time_label_x, height - 215, second_time or "")

    # Add vertical space (3 rem, ~30px, 1 rem = 10px)
    # pdf.translate(0, -20)

    # Middle Column: Fahrzeug/Kennzeichen
    pdf.setFont("Helvetica-Bold", 10)
    vehicle_label = "Fahrzeug/Kennzeichen"
    vehicle_label_x = (width - pdf.stringWidth(vehicle_label, "Helvetica-Bold", 10)) / 2
    pdf.drawString(vehicle_label_x, height - 175, vehicle_label)

    pdf.setFont("Helvetica", 10)

    vehicle_id = transaction.vehicle_id if transaction.vehicle_id not in [None, "", "None"] else None
    license_plate = transaction.license_plate if transaction.license_plate not in [None, "", "None"] else None

    y = height - 195  # Start below label

    if vehicle_id:
        text = vehicle_id
        text_x = (width - pdf.stringWidth(text, "Helvetica", 10)) / 2
        pdf.drawString(text_x, y, text)
        y -= 14

    if license_plate:
        text = license_plate
        text_x = (width - pdf.stringWidth(text, "Helvetica", 10)) / 2
        pdf.drawString(text_x, y, text)
        y -= 14

    if not vehicle_id and not license_plate:
        text = "N/A"
        text_x = (width - pdf.stringWidth(text, "Helvetica", 10)) / 2
        pdf.drawString(text_x, y, text)

    # Right Column: Gewicht
    pdf.setFont("Helvetica-Bold", 10)
    gewicht_label_text = "Gewicht"
    gewicht_label_width = pdf.stringWidth(gewicht_label_text, "Helvetica-Bold", 10)
    gewicht_label_x = (width - 103) - gewicht_label_width
    pdf.drawString(gewicht_label_x, height - 175, gewicht_label_text or "")

    # Gross Weight
    pdf.setFont("Helvetica", 10)
    gross_weight_value = f"{int(transaction.gross_weight)}" if transaction.gross_weight else "N/A"
    gross_weight_width = pdf.stringWidth(gross_weight_value, "Helvetica", 10)
    pdf.drawString((width - 103) - gross_weight_width, height - 195, gross_weight_value or "")
    pdf.drawString(width - 85 - pdf.stringWidth("kg", "Helvetica", 10), height - 195, "kg")

    # Net Weight
    net_weight_value = f"{int(transaction.net_weight)}" if transaction.net_weight else "N/A"
    net_weight_width = pdf.stringWidth(net_weight_value, "Helvetica", 10)
    pdf.drawString((width - 103) - net_weight_width, height - 215, net_weight_value or "")
    pdf.drawString(width - 85 - pdf.stringWidth("kg", "Helvetica", 10), height - 215, "kg")

    # Difference
    pdf.setFont("Helvetica-Bold", 10)
    if transaction.gross_weight is not None and transaction.net_weight is not None:
        diff_weight = int(transaction.tare_weight)
        diff_text = f"{diff_weight}"
    else:
        diff_text = "N/A"
    diff_text_width = pdf.stringWidth(diff_text, "Helvetica-Bold", 10)
    pdf.drawString((width - 103) - diff_text_width, height - 235, diff_text or "")
    pdf.drawString(width - 85 - pdf.stringWidth("kg", "Helvetica-Bold", 10), height - 235, "kg")
    pdf.drawString(width - 50 - pdf.stringWidth("netto", "Helvetica-Bold", 10), height - 235, "netto")

    # Add vertical space (3 rem, ~30px)
    pdf.translate(0, -20)

    # Bottom Row: Preis, Wäger, Kunde
    label_y = height - 265
    field_y = height - 305
    preis_label_x = 50
    waeger_label_x = (width - 150) / 2
    kunde_label_x = (width - 150)

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(preis_label_x, label_y, "Preis in CHF")
    pdf.drawString(waeger_label_x, label_y, "Wäger")
    pdf.drawString(kunde_label_x, label_y, "Kunde")

    # Preis in CHF - line
    pdf.setLineWidth(0.5)
    pdf.line(preis_label_x, field_y, preis_label_x + 100, field_y)

    # Wäger name - underlined
    pdf.setFont("Helvetica", 10)
    if transaction.operator:
        operator_name = ''.join([part[0].lower() for part in transaction.operator.split()])
    else:
        operator_name = "N/A"
    pdf.drawString(waeger_label_x, field_y + 3, operator_name or "")
    pdf.line(waeger_label_x, field_y, waeger_label_x + 100, field_y)

    # Kunde - line
    pdf.line(kunde_label_x, field_y, kunde_label_x + 100, field_y)
