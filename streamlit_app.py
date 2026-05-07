from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import httpx
import streamlit as st


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
PAGE_SIZE = 20
PLATFORMS = ["whatsapp", "facebook_messenger", "instagram", "telegram", "snapchat", "sms", "email", "linkedin", "twitter_x", "ai"]


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; }
        div[data-testid="stMetric"] {
            background: #101722;
            border: 1px solid #223044;
            border-radius: 10px;
            padding: 14px;
        }
        .m-card {
            background: #111827;
            border: 1px solid #263244;
            border-radius: 10px;
            padding: 14px 16px;
            margin: 10px 0;
        }
        .m-card strong { color: #f8fafc; }
        .m-muted { color: #94a3b8; font-size: 0.92rem; }
        .m-pill {
            display: inline-block;
            padding: 2px 9px;
            border-radius: 999px;
            background: #083344;
            color: #22d3ee;
            font-size: 0.78rem;
            margin-right: 6px;
        }
        .m-bubble-user {
            background: #06b6d4;
            color: #001018;
            padding: 10px 12px;
            border-radius: 12px;
            margin: 8px 0 8px auto;
            max-width: 72%;
        }
        .m-bubble-other {
            background: #1f2937;
            color: #f8fafc;
            padding: 10px 12px;
            border-radius: 12px;
            margin: 8px auto 8px 0;
            max-width: 72%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        clean[key] = value
    return clean


def _api_base_url() -> str:
    return st.session_state.get("api_base_url", DEFAULT_API_BASE_URL).rstrip("/")


def _headers() -> dict[str, str]:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_request(method: str, path: str, *, json_body: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, str | None]:
    url = f"{_api_base_url()}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(method, url, headers=_headers(), json=json_body, params=params)
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        if response.status_code >= 400:
            return None, f"{response.status_code}: {payload}"
        return payload, None
    except httpx.RequestError as exc:
        return None, f"Request failed: {exc}"


def unwrap_data(payload: dict[str, Any] | None) -> Any:
    if not payload:
        return None
    return payload.get("data", payload)


def render_response(payload: Any, *, title: str = "Response") -> None:
    if payload is None:
        return
    with st.expander(title, expanded=False):
        st.json(payload)


def show_cards(items: list[dict[str, Any]], *, title_key: str, subtitle_keys: list[str] | None = None, badge_key: str | None = None) -> None:
    if not items:
        st.caption("No items yet.")
        return
    for item in items:
        title = item.get(title_key) or item.get("title") or item.get("name") or item.get("id")
        badge = item.get(badge_key) if badge_key else None
        subtitles = []
        for key in subtitle_keys or []:
            value = item.get(key)
            if value not in (None, "", []):
                subtitles.append(f"{key.replace('_', ' ').title()}: {value}")
        badge_html = f"<span class='m-pill'>{badge}</span>" if badge else ""
        st.markdown(
            f"<div class='m-card'>{badge_html}<strong>{title}</strong><div class='m-muted'>{' | '.join(subtitles)}</div></div>",
            unsafe_allow_html=True,
        )


def display_error(error: str | None) -> bool:
    if error:
        st.error(error)
        return True
    return False


def login_panel() -> None:
    st.sidebar.header("API")
    st.sidebar.text_input("Base URL", key="api_base_url", value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL))
    health_col, logout_col = st.sidebar.columns(2)
    if health_col.button("Health"):
        payload, error = api_request("GET", "/health")
        if error:
            st.sidebar.error(error)
        else:
            st.sidebar.success("Healthy")
            st.sidebar.json(payload)
    if logout_col.button("Logout"):
        st.session_state.pop("access_token", None)
        st.session_state.pop("current_user", None)
        st.rerun()

    auth_tab, signup_tab = st.sidebar.tabs(["Login", "Signup"])
    with auth_tab:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            payload, error = api_request("POST", "/api/v1/auth/login", json_body={"email": email, "password": password})
            if error:
                st.error(error)
                return
            data = unwrap_data(payload) or {}
            token = data.get("access_token")
            if not token:
                st.error("Login response did not include access_token.")
                return
            st.session_state["access_token"] = token
            st.session_state["current_user"] = data.get("user")
            st.success("Logged in")
            st.rerun()
    with signup_tab:
        full_name = st.text_input("Full name", key="signup_name")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account", use_container_width=True):
            payload, error = api_request(
                "POST",
                "/api/v1/auth/register",
                json_body={"full_name": full_name, "email": signup_email, "password": signup_password},
            )
            st.error(error) if error else st.success("Account created. Check OTP email, then verify below.")
            render_response(payload, title="Signup debug")
        otp = st.text_input("OTP code", key="signup_otp")
        if st.button("Verify OTP", use_container_width=True):
            payload, error = api_request(
                "POST",
                "/api/v1/auth/verify-otp",
                json_body={"email": signup_email, "code": otp, "purpose": "signup"},
            )
            st.error(error) if error else st.success("Verified. Login now.")
            render_response(payload, title="Verify debug")

    user = st.session_state.get("current_user")
    if user:
        st.sidebar.caption(f"Signed in as {user.get('email') or user.get('full_name')}")


def auth_required() -> bool:
    if st.session_state.get("access_token"):
        return True
    st.info("Login from the sidebar to use protected backend APIs.")
    return False


def render_home() -> None:
    st.subheader("Live Dashboard")
    if not auth_required():
        return
    payload, error = api_request("GET", "/api/v1/smartflow/home")
    if display_error(error):
        return
    data = unwrap_data(payload) or {}
    cols = st.columns(4)
    stats = data.get("stats") or data.get("summary") or {}
    if not stats:
        stats = {
            "contacts": len((data.get("contacts") or {}).get("items", [])) if isinstance(data.get("contacts"), dict) else 0,
            "unread": ((data.get("messages") or {}).get("summary") or {}).get("total_unread", 0) if isinstance(data.get("messages"), dict) else 0,
            "notifications": ((data.get("notifications") or {}).get("summary") or {}).get("unread_count", 0) if isinstance(data.get("notifications"), dict) else 0,
            "integrations": len(data.get("integrations") or []),
        }
    for index, (label, value) in enumerate(list(stats.items())[:4]):
        cols[index % 4].metric(label.replace("_", " ").title(), value)

    st.markdown("#### Quick Actions")
    c1, c2, c3 = st.columns(3)
    if c1.button("Create Sample Contacts", use_container_width=True):
        seed_sample_contacts()
    if c2.button("Create Sample Conversation", use_container_width=True):
        seed_sample_conversation()
    if c3.button("Refresh Dashboard", use_container_width=True):
        st.rerun()
    render_response(data, title="Dashboard debug JSON")


def seed_sample_contacts() -> None:
    samples = [
        {"name": "Sarah Jenkins", "email": "sarah@example.com", "phone": "+15550123456", "company": "Acme Corp"},
        {"name": "Alex Rivera", "email": "alex@example.com", "phone": "+15550987654", "company": "Mabdel"},
    ]
    created = 0
    for sample in samples:
        _, error = api_request("POST", "/api/v1/smartflow/contacts", json_body=sample)
        if not error:
            created += 1
    st.success(f"{created} sample contact created.")


def seed_sample_conversation() -> None:
    contact_payload, error = api_request(
        "POST",
        "/api/v1/smartflow/contacts",
        json_body={"name": "Unified Inbox Lead", "email": "lead@example.com", "phone": "+15550001111"},
    )
    if display_error(error):
        return
    contact_id = (unwrap_data(contact_payload) or {}).get("id")
    conversation_payload, error = api_request(
        "POST",
        "/api/v1/smartflow/conversations",
        json_body={"contact_id": contact_id, "type": "direct", "platform": "whatsapp", "member_ids": []},
    )
    if display_error(error):
        return
    conversation_id = (unwrap_data(conversation_payload) or {}).get("id")
    _, error = api_request(
        "POST",
        "/api/v1/smartflow/messages",
        json_body={
            "conversation_id": conversation_id,
            "contact_id": contact_id,
            "platform": "whatsapp",
            "direction": "inbound",
            "content": "Hi, I want to discuss pricing and schedule a call.",
        },
    )
    st.error(error) if error else st.success("Sample WhatsApp-style conversation created.")


def render_contacts() -> None:
    st.subheader("Contacts")
    if not auth_required():
        return
    search = st.text_input("Search contacts")
    payload, error = api_request("GET", "/api/v1/smartflow/contacts", params={"page": 1, "page_size": PAGE_SIZE, "search": search})
    if not display_error(error):
        data = unwrap_data(payload) or {}
        items = data.get("items", [])
        show_cards(items, title_key="name", subtitle_keys=["email", "phone", "company", "presence"], badge_key="presence")
        render_response(data, title="Contacts debug JSON")

    with st.form("create_contact_form", clear_on_submit=True):
        st.markdown("#### Add Contact")
        name = st.text_input("Name", key="contact_name")
        email = st.text_input("Email", key="contact_email")
        phone = st.text_input("Phone", key="contact_phone")
        company = st.text_input("Company", key="contact_company")
        submitted = st.form_submit_button("Create Contact", type="primary")
        if submitted:
            body = _clean_payload({"name": name, "email": email, "phone": phone, "company": company})
            payload, error = api_request("POST", "/api/v1/smartflow/contacts", json_body=body)
            st.error(error) if error else st.success("Contact created")
            render_response(payload, title="Create contact debug")


def render_conversations() -> None:
    st.subheader("Unified Conversations")
    if not auth_required():
        return
    platforms = st.multiselect(
        "Platforms",
        PLATFORMS,
        default=[],
    )
    search = st.text_input("Search conversations")
    params = {"page": 1, "page_size": PAGE_SIZE, "search": search}
    if platforms:
        params["platforms"] = ",".join(platforms)
    payload, error = api_request("GET", "/api/v1/smartflow/conversations", params=params)
    if display_error(error):
        return
    data = unwrap_data(payload) or {}
    items = data.get("items", [])
    st.metric("Unread Messages", (data.get("summary") or {}).get("total_unread", 0))
    left, right = st.columns([0.9, 1.1])
    with left:
        st.markdown("#### Inbox")
        for item in items:
            label = f"{item.get('platform_label', item.get('platform'))} | {item.get('contact_name') or item.get('title') or 'Conversation'}"
            preview = item.get("last_message_preview") or "No messages yet"
            unread = item.get("unread_count", 0)
            if st.button(f"{label}\n\n{preview} ({unread} unread)", key=f"open_conv_{item['id']}", use_container_width=True):
                st.session_state["selected_conversation_id"] = item["id"]
                st.session_state["selected_conversation"] = item
        render_response(data, title="Inbox debug JSON")

    with right:
        selected_id = st.session_state.get("selected_conversation_id")
        selected = st.session_state.get("selected_conversation") or {}
        st.markdown(f"#### {selected.get('contact_name') or selected.get('title') or 'Conversation'}")
        if not selected_id:
            st.info("Select a conversation from the inbox.")
            return
        messages_payload, error = api_request("GET", f"/api/v1/smartflow/conversations/{selected_id}/messages", params={"page": 1, "page_size": 50})
        if display_error(error):
            return
        messages = (unwrap_data(messages_payload) or {}).get("items", [])
        for message in reversed(messages):
            css = "m-bubble-user" if message.get("direction") == "outbound" else "m-bubble-other"
            sender = "You" if message.get("direction") == "outbound" else message.get("sender_name", "Contact")
            st.markdown(
                f"<div class='{css}'><strong>{sender}</strong><br>{message.get('content', '')}<div class='m-muted'>{message.get('display_time_label') or message.get('timestamp') or ''}</div></div>",
                unsafe_allow_html=True,
            )
        reply = st.chat_input("Type a real outbound message")
        if reply:
            payload, error = api_request(
                "POST",
                "/api/v1/smartflow/messages",
                json_body={
                    "conversation_id": selected_id,
                    "contact_id": selected.get("contact_id"),
                    "platform": selected.get("platform", "whatsapp"),
                    "direction": "outbound",
                    "content": reply,
                },
            )
            st.error(error) if error else st.rerun()


def render_integrations() -> None:
    st.subheader("Social Integrations")
    if not auth_required():
        return
    payload, error = api_request("GET", "/api/v1/smartflow/integrations/status")
    if display_error(error):
        return
    data = unwrap_data(payload) or {}
    summary = data.get("summary") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Connected", summary.get("connected_count", 0))
    c2.metric("Needs Attention", summary.get("needs_attention_count", 0))
    c3.metric("Message Sync Enabled", summary.get("message_sync_enabled_count", 0))
    for item in data.get("items", []):
        st.markdown(
            f"<div class='m-card'><span class='m-pill'>{item.get('status')}</span><strong>{item.get('platform_label')}</strong>"
            f"<div class='m-muted'>{item.get('description')} | sync: {item.get('sync_status')} | webhook: {item.get('webhook_status')}</div></div>",
            unsafe_allow_html=True,
        )
    render_response(data, title="Integration debug JSON")

    with st.expander("Start OAuth"):
        platform = st.selectbox("Platform", ["instagram", "facebook_messenger", "whatsapp", "snapchat", "linkedin", "twitter_x"])
        if st.button("Get OAuth URL"):
            payload, error = api_request("GET", f"/api/v1/smartflow/integrations/{platform}/oauth/start")
            if error:
                st.error(error)
            else:
                data = unwrap_data(payload) or {}
                st.link_button("Open Provider OAuth", data.get("auth_url", "#"))
                st.json(data)

    with st.expander("Manual token connect / sync"):
        platform = st.selectbox("Connect platform", ["instagram", "facebook_messenger", "whatsapp", "snapchat", "linkedin", "twitter_x"], key="manual_platform")
        access_token = st.text_input("Access token", type="password")
        external_account_id = st.text_input("External account ID")
        external_account_name = st.text_input("External account name")
        if st.button("Connect Token"):
            body = _clean_payload(
                {
                    "platform": platform,
                    "access_token": access_token,
                    "external_account_id": external_account_id,
                    "external_account_name": external_account_name,
                }
            )
            payload, error = api_request("POST", "/api/v1/smartflow/integrations", json_body=body)
            st.error(error) if error else st.success("Connected")
            render_response(payload)
        if st.button("Run Sync"):
            payload, error = api_request("POST", f"/api/v1/smartflow/integrations/{platform}/sync")
            st.error(error) if error else st.json(unwrap_data(payload))


def render_invoices() -> None:
    st.subheader("Invoices")
    if not auth_required():
        return
    payload, error = api_request("GET", "/api/v1/invoices", params={"page": 1, "page_size": PAGE_SIZE})
    if not display_error(error):
        data = unwrap_data(payload) or {}
        summary = data.get("summary") or {}
        cols = st.columns(3)
        cols[0].metric("Invoices", summary.get("total_invoices", len(data.get("items", []))))
        cols[1].metric("Outstanding", summary.get("total_outstanding", 0))
        cols[2].metric("Paid", summary.get("paid_invoices", 0))
        show_cards(data.get("items", []), title_key="client_name", subtitle_keys=["invoice_number", "status", "total_amount", "due_date"], badge_key="status")
        render_response(data, title="Invoices debug JSON")

    with st.form("create_invoice_form", clear_on_submit=False):
        st.markdown("#### Create Real Invoice")
        client_name = st.text_input("Client name", key="invoice_client")
        client_email = st.text_input("Client email", key="invoice_email")
        amount = st.number_input("Amount", min_value=0.0, step=50.0)
        due_date = st.date_input("Due date", value=date.today())
        description = st.text_area("Description", value="Professional services")
        submitted = st.form_submit_button("Create Invoice", type="primary")
        if submitted:
            body = {
                "client_name": client_name,
                "client_email": client_email,
                "issue_date": date.today().isoformat(),
                "due_date": due_date.isoformat(),
                "currency": "USD",
                "items": [{"description": description, "quantity": 1, "unit_price": amount}],
            }
            payload, error = api_request("POST", "/api/v1/invoices", json_body=_clean_payload(body))
            st.error(error) if error else st.success("Invoice created")
            render_response(payload, title="Created invoice debug")


def render_documents(kind: str) -> None:
    title = "Leases" if kind == "leases" else "Agreements"
    st.subheader(title)
    if not auth_required():
        return
    status_filter = st.text_input("Status filter", value="all" if kind == "leases" else "")
    params = {"page": 1, "page_size": PAGE_SIZE}
    if status_filter:
        params["status"] = status_filter
    payload, error = api_request("GET", f"/api/v1/smartflow/{kind}", params=params)
    if not display_error(error):
        data = unwrap_data(payload) or {}
        show_cards(
            data.get("items", []),
            title_key="tenant_name" if kind == "leases" else "title",
            subtitle_keys=["property_address", "client_name", "status", "created_at", "monthly_rent_label"],
            badge_key="status",
        )
        render_response(data, title=f"{title} debug JSON")

    with st.expander(f"AI generate and save {kind[:-1]}", expanded=True):
        prompt = st.text_area("Prompt", value=f"Create a professional {kind[:-1]} draft.")
        if st.button(f"Generate Draft"):
            endpoint = f"/api/v1/smartflow/{kind}/generate"
            payload, error = api_request("POST", endpoint, json_body={"prompt": prompt})
            if display_error(error):
                return
            draft = unwrap_data(payload) or {}
            st.session_state[f"{kind}_draft"] = draft
            st.success("Draft generated. Review below, then save.")
        draft = st.session_state.get(f"{kind}_draft")
        if draft:
            st.text_area("Generated content", value=draft.get("content", ""), height=260, key=f"{kind}_draft_content")
            if st.button(f"Save {kind[:-1].title()}"):
                if kind == "leases":
                    body = {
                        "prompt": prompt,
                        "property_address": draft.get("property_address") or "123 Main Street",
                        "property_type": draft.get("property_type") or "apartment",
                        "landlord_name": draft.get("landlord_name") or "Mabdel Properties",
                        "tenant_name": draft.get("tenant_name") or "Tenant",
                        "tenant_email": draft.get("tenant_email") or "tenant@example.com",
                        "monthly_rent_cents": draft.get("monthly_rent_cents") or 120000,
                        "security_deposit_cents": draft.get("security_deposit_cents") or 120000,
                        "rent_due_day": draft.get("rent_due_day") or 1,
                        "start_date": draft.get("start_date") or date.today().isoformat(),
                        "end_date": draft.get("end_date") or date(date.today().year + 1, date.today().month, date.today().day).isoformat(),
                        "content": st.session_state.get(f"{kind}_draft_content"),
                        "status": "draft",
                    }
                else:
                    body = {
                        "title": draft.get("title") or "Generated Agreement",
                        "client_name": draft.get("client_name") or "Client",
                        "client_email": draft.get("client_email") or "client@example.com",
                        "agreement_type": draft.get("agreement_type") or "contract",
                        "priority": draft.get("priority") or "standard",
                        "content": st.session_state.get(f"{kind}_draft_content"),
                        "smart_fields": draft.get("smart_fields") or [],
                    }
                payload, error = api_request("POST", f"/api/v1/smartflow/{kind}", json_body=body)
                st.error(error) if error else st.success(f"{kind[:-1].title()} saved")
                render_response(payload, title=f"Saved {kind[:-1]} debug")


def render_bulk_messages() -> None:
    st.subheader("Bulk Messages")
    if not auth_required():
        return
    payload, error = api_request("GET", "/api/v1/smartflow/bulk-messages", params={"page": 1, "page_size": PAGE_SIZE})
    if not display_error(error):
        data = unwrap_data(payload) or {}
        show_cards(data.get("items", []), title_key="subject", subtitle_keys=["channel", "status", "recipient_count", "sent_count"], badge_key="status")
        render_response(data, title="Bulk messages debug JSON")

    with st.form("bulk_message_form"):
        st.markdown("#### Create Real Bulk Message")
        channel = st.selectbox("Channel", ["email", "sms", "whatsapp"])
        subject = st.text_input("Subject")
        content = st.text_area("Content")
        contact_ids = st.text_area("Contact IDs, one per line")
        recipient_emails = st.text_area("Extra recipient emails, one per line")
        send_now = st.checkbox("Send now")
        submitted = st.form_submit_button("Create Bulk Message")
        if submitted:
            body = _clean_payload(
                {
                    "channel": channel,
                    "subject": subject,
                    "content": content,
                    "contact_ids": [line.strip() for line in contact_ids.splitlines() if line.strip()],
                    "recipient_emails": [line.strip() for line in recipient_emails.splitlines() if line.strip()],
                    "send_now": send_now,
                }
            )
            payload, error = api_request("POST", "/api/v1/smartflow/bulk-messages", json_body=body)
            st.error(error) if error else st.success("Bulk message created")
            render_response(payload, title="Created bulk message debug")


def render_calls() -> None:
    st.subheader("Calls")
    if not auth_required():
        return
    status_filter = st.text_input("Status")
    payload, error = api_request("GET", "/api/v1/smartflow/calls", params=_clean_payload({"page": 1, "page_size": PAGE_SIZE, "status": status_filter}))
    if not display_error(error):
        data = unwrap_data(payload) or {}
        show_cards(data.get("items", []), title_key="display_name", subtitle_keys=["phone_number", "status", "duration_label", "timestamp"], badge_key="status")
        render_response(data, title="Calls debug JSON")

    with st.expander("Outbound call"):
        phone = st.text_input("Phone number")
        if st.button("Call"):
            payload, error = api_request("POST", "/api/v1/smartflow/calls/outbound", json_body={"phone_number": phone})
            st.error(error) if error else st.success("Call requested")
            render_response(payload)


def render_notifications() -> None:
    st.subheader("Notifications")
    if not auth_required():
        return
    unread_only = st.checkbox("Unread only")
    payload, error = api_request("GET", "/api/v1/smartflow/notifications", params={"page": 1, "page_size": PAGE_SIZE, "unread_only": unread_only})
    if display_error(error):
        return
    data = unwrap_data(payload) or {}
    show_cards(data.get("items", []), title_key="title", subtitle_keys=["body", "display_time_label", "type"], badge_key="date_bucket")
    render_response(data, title="Notifications debug JSON")
    if st.button("Mark all read"):
        payload, error = api_request("POST", "/api/v1/smartflow/notifications/mark-all-read")
        st.error(error) if error else st.success("Marked all read")
        render_response(payload)


def render_ai_workflow() -> None:
    st.subheader("Use Mabdel AI")
    if not auth_required():
        return
    intent = st.selectbox("Intent", ["invoice", "bulk_message", "calendar", "lease", "agreement"])
    prompt = st.text_area("Command", value="Create an invoice for Alex for $1200 due next Friday")
    if st.button("Run AI and Prepare Form", type="primary"):
        payload, error = api_request("POST", "/api/v1/smartflow/ai/workflow-prefill", json_body={"workflow_intent": intent, "message": prompt})
        if display_error(error):
            return
        data = unwrap_data(payload) or {}
        st.session_state["last_ai_prefill"] = data
        st.success(f"Ready for: {data.get('screen') or data.get('workflow_intent') or intent}")
        st.markdown(f"**Suggested action:** `{data.get('next_action')}`")
        st.markdown(f"**Frontend route:** `{data.get('frontend_route') or data.get('route')}`")
        prefill = data.get("prefill") or {}
        st.json(prefill)
        render_response(data, title="AI workflow debug JSON")

    with st.expander("Raw AI chat"):
        message = st.text_area("Message", key="ai_chat_message")
        if st.button("Send Chat"):
            payload, error = api_request("POST", "/api/v1/smartflow/ai/chat", json_body={"message": message})
            st.error(error) if error else st.json(unwrap_data(payload))


def render_api_console() -> None:
    st.subheader("Raw API Console")
    if not auth_required():
        return
    method = st.selectbox("Method", ["GET", "POST", "PATCH", "PUT", "DELETE"])
    path = st.text_input("Path", value="/api/v1/smartflow/home")
    params_text = st.text_area("Query params JSON", value="{}")
    body_text = st.text_area("Body JSON", value="{}")
    if st.button("Send Request", type="primary"):
        try:
            params = json.loads(params_text or "{}")
            body = json.loads(body_text or "{}")
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
            return
        payload, error = api_request(method, path, params=params, json_body=body if method != "GET" else None)
        st.error(error) if error else st.json(payload)


def main() -> None:
    st.set_page_config(page_title="Mabdel Live App", page_icon="M", layout="wide")
    inject_styles()
    st.title("Mabdel Live App")
    st.caption("Real Streamlit frontend connected to the running Mabdel backend.")
    login_panel()

    pages = {
        "Dashboard": render_home,
        "Contacts": render_contacts,
        "Unified Conversations": render_conversations,
        "Social Integrations": render_integrations,
        "Invoices": render_invoices,
        "Bulk Messages": render_bulk_messages,
        "Leases": lambda: render_documents("leases"),
        "Agreements": lambda: render_documents("agreements"),
        "Calls": render_calls,
        "Notifications": render_notifications,
        "AI Workflow": render_ai_workflow,
        "Raw API Console": render_api_console,
    }
    selected = st.sidebar.radio("Pages", list(pages.keys()))
    pages[selected]()


if __name__ == "__main__":
    main()
