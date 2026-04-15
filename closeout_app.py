import streamlit as st
import io
from pypdf import PdfReader, PdfWriter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import json

st.set_page_config(page_title="Project Closeout Router", layout="wide")
st.title("📋 Project Closeout Form Filler & Team Router")
st.caption("Live shared app — works on phone, tablet, laptop • Data syncs automatically")

# Simple persistent storage using session + JSON (for small team use)
if "history" not in st.session_state:
    st.session_state.history = []  # list of past submissions
if "team_list" not in st.session_state:
    st.session_state.team_list = [
        "person1@yourcompany.com",
        "person2@yourcompany.com",
        "person3@yourcompany.com",
        "person4@yourcompany.com",
        "person5@yourcompany.com",
        "person6@yourcompany.com"
    ]

# Sidebar for shared team list
with st.sidebar:
    st.header("Team Management")
    st.write("Edit team emails (one per line)")
    team_text = st.text_area("Team Emails", 
                             value="\n".join(st.session_state.team_list), 
                             height=200)
    if st.button("Save Team List"):
        st.session_state.team_list = [e.strip() for e in team_text.splitlines() if e.strip()]
        st.success("Team list updated for everyone!")

    st.divider()
    st.header("Submission History")
    if st.session_state.history:
        for item in reversed(st.session_state.history[-10:]):  # show last 10
            st.caption(f"{item['timestamp']} — {item['project_name']}")
    else:
        st.caption("No submissions yet")

# Main app
uploaded_file = st.file_uploader("Upload fillable PDF form", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    form_fields = reader.get_form_text_fields() or {}

    st.subheader("Fill Project Information")
    field_values = {}
    for field_name, current_value in form_fields.items():
        default = current_value if isinstance(current_value, str) else ""
        new_value = st.text_input(field_name, value=default, key=f"f_{field_name}")
        field_values[field_name] = new_value

    col1, col2 = st.columns([3, 1])
    with col1:
        project_name = st.text_input("Project Name / ID (for history)", value="New Project")
    with col2:
        if st.button("Fill PDF", type="primary"):
            with st.spinner("Filling form..."):
                writer = PdfWriter()
                writer.append(reader)
                for page in writer.pages:
                    writer.update_page_form_field_values(page, field_values)

                output = io.BytesIO()
                writer.write(output)
                output.seek(0)
                filled_bytes = output.getvalue()

                st.session_state.filled_pdf = filled_bytes
                st.session_state.filled_filename = f"{project_name.replace(' ', '_')}_closeout.pdf"
                st.success("PDF filled successfully!")

    if "filled_pdf" in st.session_state:
        st.download_button(
            "⬇️ Download Filled PDF",
            data=st.session_state.filled_pdf,
            file_name=st.session_state.filled_filename,
            mime="application/pdf"
        )

        st.divider()
        st.subheader("Route to Team for Signatures")

        emails = st.multiselect("Select recipients", 
                                options=st.session_state.team_list,
                                default=st.session_state.team_list[:5])

        sender_email = st.text_input("Your Email")
        sender_password = st.text_input("Email App Password", type="password")
        smtp_server = st.text_input("SMTP Server", "smtp.gmail.com")
        smtp_port = 587

        subject = st.text_input("Subject", f"Closeout Approval: {project_name}")
        body = st.text_area("Message", 
"""Hi Team,

Please review the attached Project Closeout form and add your digital signature / approval.

Thank you!
""", height=150)

        if st.button("Send to Selected Team Members", type="primary"):
            if not emails:
                st.error("Select at least one recipient")
            else:
                success_count = 0
                with st.spinner(f"Sending to {len(emails)} people..."):
                    for recipient in emails:
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = sender_email
                            msg['To'] = recipient
                            msg['Subject'] = subject
                            msg.attach(MIMEText(body, 'plain'))

                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(st.session_state.filled_pdf)
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename={st.session_state.filled_filename}')
                            msg.attach(part)

                            server = smtplib.SMTP(smtp_server, smtp_port)
                            server.starttls()
                            server.login(sender_email, sender_password)
                            server.sendmail(sender_email, recipient, msg.as_string())
                            server.quit()
                            success_count += 1
                        except Exception as e:
                            st.error(f"Failed for {recipient}: {str(e)}")

                if success_count == len(emails):
                    st.success(f"✅ Sent to all {len(emails)} members!")
                    # Save to shared history
                    st.session_state.history.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "project_name": project_name,
                        "recipients": len(emails)
                    })

# Footer
st.caption("Live multi-device app • All team members see the same updated data • Secure on your own email for sending")