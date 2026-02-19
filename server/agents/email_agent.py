"""Email Agent - IMAP/SMTP based email management."""

from __future__ import annotations

import asyncio
import email
import imaplib
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, Task, AgentResponse, AgentStatus


@dataclass
class EmailPlan:
    action: str
    mailbox: str
    query: str
    count: int
    to: List[str]
    subject: str
    body: str
    reason: str


class EmailAgent(BaseAgent):
    """Reads, searches, drafts, and sends email via IMAP/SMTP."""

    def __init__(self, agent_id: str = "email_agent_v1"):
        super().__init__(
            agent_id=agent_id,
            name="Email Agent",
            description="Manage email: read, summarize, draft, send, and search."
        )

    def can_handle_task(self, task: Task) -> bool:
        query = str(task.metadata.get("query", "")).lower()
        keywords = ["email", "inbox", "mail", "gmail", "outlook", "send", "draft", "reply"]
        return any(k in query for k in keywords)

    async def process_task(self, task: Task) -> AgentResponse:
        self.status = AgentStatus.RUNNING
        task_id = task.metadata.get("parent_task_id") or task.id
        query = task.metadata.get("query", "")
        permission_callback = task.metadata.get("permission_callback")

        await self.emit_event("active_agent", task_id, {"agent": self.name})
        await self.emit_event("agent_state", task_id, {"state": "executing", "agent": self.name})
        await self.emit_event("agent_activity", task_id, {"agent": self.name, "message": "Planning email action"})

        plan = await self._create_plan(task, query)
        if plan.action == "clarify":
            return AgentResponse(agent_id=self.agent_id, success=False, error="clarification_required", metadata={
                "missing_fields": plan.reason
            })

        try:
            if plan.action in {"read", "search", "summarize"}:
                messages = await self._read_messages(plan)
                if plan.action == "summarize":
                    summary = await self._summarize_messages(task, messages)
                    return AgentResponse(agent_id=self.agent_id, success=True, result={
                        "action": plan.action,
                        "mailbox": plan.mailbox,
                        "count": len(messages),
                        "summary": summary,
                    })
                return AgentResponse(agent_id=self.agent_id, success=True, result={
                    "action": plan.action,
                    "mailbox": plan.mailbox,
                    "count": len(messages),
                    "messages": messages,
                })

            if plan.action == "draft":
                return AgentResponse(agent_id=self.agent_id, success=True, result={
                    "action": "draft",
                    "to": plan.to,
                    "subject": plan.subject,
                    "body": plan.body,
                })

            if plan.action == "send":
                if permission_callback:
                    await self.emit_event("agent_state", task_id, {"state": "waiting_for_permission", "agent": self.name})
                    approved = await permission_callback(
                        f"send email to {', '.join(plan.to)}",
                        f"subject={plan.subject}",
                        "high",
                    )
                    if not approved:
                        return AgentResponse(agent_id=self.agent_id, success=False, error="permission_denied")
                result = await self._send_message(plan)
                return AgentResponse(agent_id=self.agent_id, success=True, result=result)

            return AgentResponse(agent_id=self.agent_id, success=False, error="unsupported_action")
        except Exception as exc:
            return AgentResponse(agent_id=self.agent_id, success=False, error=str(exc))
        finally:
            self.status = AgentStatus.COMPLETED

    async def _create_plan(self, task: Task, query: str) -> EmailPlan:
        llm = self.get_llm(task)
        system_prompt = """
You are an email planner. Return JSON only:
{
  "action": "read|search|summarize|draft|send|clarify",
  "mailbox": "INBOX",
  "query": "search terms",
  "count": 5,
  "to": ["email@example.com"],
  "subject": "subject",
  "body": "body",
  "reason": "missing_fields"
}
Rules:
- For read/summarize, use mailbox and count.
- For search, use query.
- For draft/send, require to, subject, body.
- If required fields missing, action=clarify and reason lists missing fields.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
            import re, json
            match = re.search(r"\{.*\}", content, re.DOTALL)
            data = json.loads(match.group(0)) if match else {}
        except Exception:
            data = {}

        action = str(data.get("action", "read")).strip().lower()
        mailbox = str(data.get("mailbox", "INBOX")).strip() or "INBOX"
        count = int(data.get("count", 5) or 5)
        query_text = str(data.get("query", "")).strip()
        to = data.get("to") or []
        subject = str(data.get("subject", "")).strip()
        body = str(data.get("body", "")).strip()

        missing = []
        if action in {"draft", "send"}:
            if not to:
                missing.append("to")
            if not subject:
                missing.append("subject")
            if not body:
                missing.append("body")
        if action == "search" and not query_text:
            missing.append("query")
        if action in {"read", "summarize"} and count <= 0:
            missing.append("count")

        if missing:
            return EmailPlan(
                action="clarify",
                mailbox=mailbox,
                query=query_text,
                count=count,
                to=to,
                subject=subject,
                body=body,
                reason=",".join(missing),
            )

        if action not in {"read", "search", "summarize", "draft", "send"}:
            action = "read"

        return EmailPlan(
            action=action,
            mailbox=mailbox,
            query=query_text,
            count=count,
            to=to,
            subject=subject,
            body=body,
            reason="",
        )

    async def _read_messages(self, plan: EmailPlan) -> List[Dict[str, Any]]:
        cfg = self._imap_config()
        if not cfg["host"] or not cfg["user"] or not cfg["password"]:
            raise RuntimeError("email_imap_not_configured")

        def _work() -> List[Dict[str, Any]]:
            client = imaplib.IMAP4_SSL(cfg["host"], cfg["port"])
            client.login(cfg["user"], cfg["password"])
            client.select(plan.mailbox)
            if plan.action == "search" and plan.query:
                status, data = client.search(None, f'(TEXT "{plan.query}")')
            else:
                status, data = client.search(None, "ALL")
            if status != "OK":
                client.logout()
                return []
            ids = data[0].split()[-plan.count :]
            results: List[Dict[str, Any]] = []
            for msg_id in ids[::-1]:
                status, msg_data = client.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                results.append({
                    "from": msg.get("From"),
                    "to": msg.get("To"),
                    "subject": msg.get("Subject"),
                    "date": msg.get("Date"),
                    "snippet": self._get_snippet(msg),
                })
            client.logout()
            return results

        return await asyncio.to_thread(_work)

    async def _send_message(self, plan: EmailPlan) -> Dict[str, Any]:
        cfg = self._smtp_config()
        if not cfg["host"] or not cfg["user"] or not cfg["password"]:
            raise RuntimeError("email_smtp_not_configured")

        def _work() -> Dict[str, Any]:
            msg = EmailMessage()
            msg["From"] = cfg["user"]
            msg["To"] = ", ".join(plan.to)
            msg["Subject"] = plan.subject
            msg.set_content(plan.body)

            if cfg["use_ssl"]:
                server = smtplib.SMTP_SSL(cfg["host"], cfg["port"])
            else:
                server = smtplib.SMTP(cfg["host"], cfg["port"])
            if cfg["use_tls"]:
                server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
            server.quit()
            return {"status": "sent", "to": plan.to, "subject": plan.subject}

        return await asyncio.to_thread(_work)

    async def _summarize_messages(self, task: Task, messages: List[Dict[str, Any]]) -> str:
        llm = self.get_llm(task)
        prompt = "Summarize the following emails succinctly:\n" + str(messages)
        response = await llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)

    def _get_snippet(self, msg: email.message.Message) -> str:
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True) or b""
                        return payload.decode(errors="ignore")[:300]
            payload = msg.get_payload(decode=True) or b""
            return payload.decode(errors="ignore")[:300]
        except Exception:
            return ""

    def _imap_config(self) -> Dict[str, Any]:
        return {
            "host": os.getenv("JARVIS_IMAP_HOST"),
            "port": int(os.getenv("JARVIS_IMAP_PORT", "993")),
            "user": os.getenv("JARVIS_EMAIL_USER"),
            "password": os.getenv("JARVIS_EMAIL_PASSWORD"),
        }

    def _smtp_config(self) -> Dict[str, Any]:
        return {
            "host": os.getenv("JARVIS_SMTP_HOST"),
            "port": int(os.getenv("JARVIS_SMTP_PORT", "587")),
            "user": os.getenv("JARVIS_EMAIL_USER"),
            "password": os.getenv("JARVIS_EMAIL_PASSWORD"),
            "use_tls": os.getenv("JARVIS_SMTP_TLS", "1") == "1",
            "use_ssl": os.getenv("JARVIS_SMTP_SSL", "0") == "1",
        }
