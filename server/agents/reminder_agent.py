import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

try:
    from mem0 import Memory
except Exception:  # pragma: no cover - optional dependency
    Memory = None

logger = logging.getLogger(__name__)


class RemAgent:
    """
    Reminder/Alarm Agent backed by mem0 for long-term, persistent scheduling.

    Responsibilities:
    - Store reminders/alarms in mem0 with metadata for filtering
    - Periodically evaluate due items and emit trigger events
    - Support cancel/update/snooze and recurring schedules
    """

    DEFAULT_AGENT_ID = "rem_agent"

    def __init__(
        self,
        *,
        agent_id: str = DEFAULT_AGENT_ID,
        memory_config: Optional[Dict[str, Any]] = None,
        min_poll_seconds: float = 0.5,
        max_poll_seconds: float = 60.0,
        analysis_interval_seconds: float = 300.0,
        autonomy_enabled: bool = True,
        confidence_threshold: float = 0.75,
    ):
        self.agent_id = agent_id
        self._callbacks: set[Callable[[str, str, Dict[str, Any]], Awaitable[None]]] = set()
        self._wake_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._min_poll_seconds = min_poll_seconds
        self._max_poll_seconds = max_poll_seconds
        self._analysis_interval_seconds = analysis_interval_seconds
        self._last_analysis_ts = 0.0
        self._autonomy_enabled = autonomy_enabled
        self._confidence_threshold = confidence_threshold
        self._submit_query_callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[str]]] = None
        self._permission_futures: Dict[str, asyncio.Future] = {}
        self._autonomous_tasks: Dict[str, Dict[str, Any]] = {}

        if Memory is None:
            logger.warning("RemAgent: mem0 not installed; reminder features disabled.")
            self.memory = None
        else:
            try:
                config = memory_config or self._default_memory_config()
                self.memory = Memory.from_config(config)
                logger.info("RemAgent: mem0 Memory initialized.")
            except Exception as exc:
                logger.warning("RemAgent: Failed to initialize mem0 Memory: %s", exc)
                self.memory = None

    def _default_memory_config(self) -> Dict[str, Any]:
        from pathlib import Path
        from os.path import join as pathjoin,exists as pathexists
        cache_dir = Path().home()
        jarvis_cache = pathjoin(cache_dir,".jarvis")
        return {
            "llm": {
                "provider": "litellm",
                "config": {"model": "huggingface/microsoft/phi-4-mini-instruct"},
            },
            "embedder": {
                "provider": "huggingface",
                "config": {"model": "multi-qa-MiniLM-L6-cos-v1"},
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "jarvis",
                    "path": pathjoin(jarvis_cache,"memory"),
                },
            },
        }

    def add_event_callback(self, callback: Callable[[str, str, Dict[str, Any]], Awaitable[None]]) -> None:
        self._callbacks.add(callback)

    def remove_event_callback(self, callback: Callable[[str, str, Dict[str, Any]], Awaitable[None]]) -> None:
        self._callbacks.discard(callback)

    def set_submit_query_callback(self, callback: Callable[[str, Dict[str, Any]], Awaitable[str]]) -> None:
        self._submit_query_callback = callback

    def clear_submit_query_callback(self) -> None:
        self._submit_query_callback = None

    def resolve_permission(self, request_id: str, approved: bool) -> bool:
        future = self._permission_futures.get(request_id)
        if future and not future.done():
            future.set_result(approved)
            return True
        return False

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def ensure_started(self) -> None:
        if self._task is None or self._task.done():
            asyncio.create_task(self.start())

    async def record_user_query(
        self,
        text: str,
        *,
        user_id: str = "default_user",
        timestamp: Optional[datetime] = None,
    ) -> None:
        if not self.memory:
            return
        ts = timestamp or datetime.now().astimezone()
        signature = self._normalize_query(text)
        metadata = {
            "kind": "user_query",
            "text": text,
            "signature": signature,
            "hour": ts.hour,
            "weekday": ts.weekday(),
            "timestamp_ts": int(ts.timestamp()),
            "timestamp_iso": ts.isoformat(),
            "created_at_ts": int(time.time()),
        }
        await asyncio.to_thread(
            self.memory.add,
            text,
            agent_id=self.agent_id,
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )
        self._wake_event.set()
    async def record_assistant_query(
        self,
        text: str,
        *,
        user_id: str = "default_user",
        timestamp: Optional[datetime] = None,
    ) -> None:
        if not self.memory:
            return
        ts = timestamp or datetime.now().astimezone()
        signature = self._normalize_query(text)
        metadata = {
            "kind": "assistant",
            "text": text,
            "signature": signature,
            "hour": ts.hour,
            "weekday": ts.weekday(),
            "timestamp_ts": int(ts.timestamp()),
            "timestamp_iso": ts.isoformat(),
            "created_at_ts": int(time.time()),
        }
        await asyncio.to_thread(
            self.memory.add,
            text,
            agent_id=self.agent_id,
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )
        self._wake_event.set()
    async def record_autonomous_result(
        self,
        task_id: str,
        accepted: bool,
        *,
        reason: Optional[str] = None,
    ) -> None:
        if not self.memory:
            return
        task_info = self._autonomous_tasks.get(task_id)
        if not task_info:
            return
        pattern_id = task_info.get("pattern_id")
        signature = task_info.get("signature")
        metadata = {
            "kind": "autonomy_execution",
            "task_id": task_id,
            "pattern_id": pattern_id,
            "signature": signature,
            "accepted": bool(accepted),
            "reason": reason,
            "timestamp_ts": int(time.time()),
        }
        await asyncio.to_thread(
            self.memory.add,
            json.dumps(metadata),
            agent_id=self.agent_id,
            user_id=task_info.get("user_id", "default_user"),
            metadata=metadata,
            infer=False,
        )
        await self._update_pattern_feedback(pattern_id, accepted)
        if not accepted:
            await self._emit_event(
                "autonomous_task_result",
                task_id,
                {"task_id": task_id, "status": "rejected", "reason": reason},
            )

    async def record_autonomous_completion(self, task_id: str, result_text: str) -> None:
        if task_id not in self._autonomous_tasks:
            return
        await self.record_autonomous_result(task_id, accepted=True)
        await self._emit_event(
            "autonomous_task_result",
            task_id,
            {"task_id": task_id, "result": result_text, "status": "completed"},
        )

    async def add_reminder(
        self,
        *,
        text: str,
        trigger_at: datetime,
        label: Optional[str] = None,
        recurrence: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        if not self.memory:
            return {"status": "error", "message": "Reminder memory not available"}

        trigger_dt = self._ensure_tz(trigger_at)
        reminder_id = str(uuid.uuid4())
        metadata = self._build_metadata(
            kind="reminder",
            reminder_id=reminder_id,
            text=text,
            label=label,
            trigger_dt=trigger_dt,
            recurrence=recurrence,
        )
        data = json.dumps({"type": "reminder", "id": reminder_id, "text": text, "label": label})

        await asyncio.to_thread(
            self.memory.add,
            data,
            agent_id=self.agent_id,
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )

        self._wake_event.set()
        return {
            "status": "success",
            "message": f"Reminder set for {trigger_dt.isoformat()}",
            "data": {"id": reminder_id, "trigger_at": trigger_dt.isoformat()},
        }

    async def add_alarm(
        self,
        *,
        time_str: str,
        label: Optional[str] = None,
        days_of_week: Optional[List[str]] = None,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        if not self.memory:
            return {"status": "error", "message": "Alarm memory not available"}

        now = datetime.now().astimezone()
        next_trigger = self._compute_next_alarm_time(time_str, days_of_week, now)
        reminder_id = str(uuid.uuid4())
        recurrence = None
        if days_of_week:
            recurrence = {"type": "weekly", "days_of_week": days_of_week, "time": time_str}

        metadata = self._build_metadata(
            kind="alarm",
            reminder_id=reminder_id,
            text=label or "Alarm",
            label=label,
            trigger_dt=next_trigger,
            recurrence=recurrence,
            time_of_day=time_str,
            days_of_week=days_of_week,
        )
        data = json.dumps(
            {
                "type": "alarm",
                "id": reminder_id,
                "label": label,
                "time": time_str,
                "days_of_week": days_of_week or [],
            }
        )

        await asyncio.to_thread(
            self.memory.add,
            data,
            agent_id=self.agent_id,
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )

        self._wake_event.set()
        return {
            "status": "success",
            "message": f"Alarm set for {next_trigger.isoformat()}",
            "data": {"id": reminder_id, "next_trigger": next_trigger.isoformat()},
        }

    async def list_items(
        self,
        *,
        kind: Optional[str] = None,
        status: Optional[List[str]] = None,
        user_id: str = "default_user",
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        if not self.memory:
            return []

        filters: Dict[str, Any] = {"agent_id": self.agent_id, "user_id": user_id}
        if kind:
            filters["kind"] = {"eq": kind}
        if status:
            filters["status"] = {"in": status}

        items = await self._list_by_filters(filters, limit)
        return [self._format_item(i) for i in items]

    async def cancel_item(self, reminder_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        item = await self._get_by_reminder_id(reminder_id, user_id=user_id)
        if not item:
            return {"status": "error", "message": "Reminder not found"}

        await self._update_payload(
            item["memory_id"],
            {"status": "cancelled", "updated_at_ts": int(time.time())},
        )
        self._wake_event.set()
        return {"status": "success", "message": "Reminder cancelled"}

    async def snooze_item(
        self,
        reminder_id: str,
        minutes: int = 5,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        item = await self._get_by_reminder_id(reminder_id, user_id=user_id)
        if not item:
            return {"status": "error", "message": "Reminder not found"}

        now = datetime.now().astimezone()
        new_trigger = now + timedelta(minutes=minutes)
        await self._update_payload(
            item["memory_id"],
            {
                "status": "snoozed",
                "trigger_at_ts": int(new_trigger.timestamp()),
                "trigger_at_iso": new_trigger.isoformat(),
                "updated_at_ts": int(time.time()),
            },
        )
        self._wake_event.set()
        return {
            "status": "success",
            "message": f"Snoozed for {minutes} minutes",
            "data": {"id": reminder_id, "trigger_at": new_trigger.isoformat()},
        }

    async def update_item(
        self,
        reminder_id: str,
        *,
        text: Optional[str] = None,
        label: Optional[str] = None,
        trigger_at: Optional[datetime] = None,
        recurrence: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        item = await self._get_by_reminder_id(reminder_id, user_id=user_id)
        if not item:
            return {"status": "error", "message": "Reminder not found"}

        updates: Dict[str, Any] = {"updated_at_ts": int(time.time())}
        if text is not None:
            updates["text"] = text
        if label is not None:
            updates["label"] = label
        if trigger_at is not None:
            trigger_dt = self._ensure_tz(trigger_at)
            updates["trigger_at_ts"] = int(trigger_dt.timestamp())
            updates["trigger_at_iso"] = trigger_dt.isoformat()
            updates["status"] = "scheduled"
        if recurrence is not None:
            updates.update(self._recurrence_metadata(recurrence))

        await self._update_payload(item["memory_id"], updates)
        self._wake_event.set()
        return {"status": "success", "message": "Reminder updated"}

    async def _run_loop(self) -> None:
        if not self.memory:
            logger.warning("RemAgent: memory unavailable, background loop disabled.")
            return

        while not self._stop_event.is_set():
            try:
                now_ts = time.time()
                if self._autonomy_enabled and now_ts - self._last_analysis_ts >= self._analysis_interval_seconds:
                    await self._analyze_and_trigger_autonomy()
                    self._last_analysis_ts = now_ts

                now_ts = int(time.time())
                due_items = await self._get_due_items(now_ts)
                for item in due_items:
                    await self._trigger_item(item)

                next_ts = await self._get_next_trigger_ts()
                next_analysis_ts = self._last_analysis_ts + self._analysis_interval_seconds
                sleep_for = self._calculate_sleep(next_ts, next_analysis_ts)

                self._wake_event.clear()
                try:
                    await asyncio.wait_for(self._wake_event.wait(), timeout=sleep_for)
                except asyncio.TimeoutError:
                    pass
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("RemAgent loop error: %s", exc)
                await asyncio.sleep(self._min_poll_seconds)

    def _calculate_sleep(self, next_ts: Optional[int], next_analysis_ts: float) -> float:
        now = time.time()
        sleep_candidates: List[float] = []
        if next_ts is not None:
            sleep_candidates.append(max(next_ts - now, self._min_poll_seconds))
        sleep_candidates.append(max(next_analysis_ts - now, self._min_poll_seconds))
        delay = min(sleep_candidates) if sleep_candidates else self._max_poll_seconds
        return min(delay, self._max_poll_seconds)

    async def _get_due_items(self, now_ts: int) -> List[Dict[str, Any]]:
        filters = {
            "agent_id": self.agent_id,
            "status": {"in": ["scheduled", "snoozed"]},
            "trigger_at_ts": {"lte": now_ts},
        }
        return await self._list_by_filters(filters, limit=1000)

    async def _get_next_trigger_ts(self) -> Optional[int]:
        filters = {
            "agent_id": self.agent_id,
            "status": {"in": ["scheduled", "snoozed"]},
        }
        items = await self._list_by_filters(filters, limit=1000)
        if not items:
            return None
        trigger_times = [i.get("trigger_at_ts") for i in items if i.get("trigger_at_ts")]
        return min(trigger_times) if trigger_times else None

    async def _trigger_item(self, item: Dict[str, Any]) -> None:
        kind = item.get("kind", "reminder")
        reminder_id = item.get("reminder_id", item.get("memory_id"))
        task_id = f"{kind}_{reminder_id}"
        payload = {
            "id": reminder_id,
            "kind": kind,
            "text": item.get("text") or item.get("label") or "Reminder",
            "label": item.get("label"),
            "trigger_at": item.get("trigger_at_iso"),
            "is_recurring": item.get("recurrence_type") not in (None, "none"),
        }

        await self._emit_event(
            "alarm_triggered" if kind == "alarm" else "reminder_triggered",
            task_id,
            payload,
        )

        await self._handle_post_trigger(item)

    async def _handle_post_trigger(self, item: Dict[str, Any]) -> None:
        recurrence_type = item.get("recurrence_type")
        if recurrence_type and recurrence_type != "none":
            next_dt = self._compute_next_recurrence(item)
            if next_dt:
                await self._update_payload(
                    item["memory_id"],
                    {
                        "trigger_at_ts": int(next_dt.timestamp()),
                        "trigger_at_iso": next_dt.isoformat(),
                        "status": "scheduled",
                        "last_triggered_ts": int(time.time()),
                        "updated_at_ts": int(time.time()),
                    },
                )
                return

        await self._update_payload(
            item["memory_id"],
            {
                "status": "completed",
                "last_triggered_ts": int(time.time()),
                "updated_at_ts": int(time.time()),
            },
        )

    async def _analyze_and_trigger_autonomy(self) -> None:
        if not self._autonomy_enabled or not self.memory:
            return

        await self._build_behavior_patterns()
        patterns = await self._list_by_filters(
            {"agent_id": self.agent_id, "kind": {"eq": "autonomy_pattern"}},
            limit=500,
        )
        if not patterns:
            return

        now = datetime.now().astimezone()
        for pattern in patterns:
            if pattern.get("confidence", 0.0) < self._confidence_threshold:
                continue
            if not self._pattern_due_now(pattern, now):
                continue

            await self._execute_autonomous_task(pattern, now)

    async def _build_behavior_patterns(self) -> None:
        window_days = 21
        window_start = int((datetime.now().astimezone() - timedelta(days=window_days)).timestamp())
        items = await self._list_by_filters(
            {
                "agent_id": self.agent_id,
                "kind": {"eq": "user_query"},
                "timestamp_ts": {"gte": window_start},
            },
            limit=2000,
        )
        if not items:
            return

        grouped: Dict[str, Dict[str, Any]] = {}
        for item in items:
            signature = item.get("signature")
            hour = item.get("hour")
            user_id = item.get("user_id", "default_user")
            if signature is None or hour is None:
                continue
            key = f"{user_id}|{signature}|{hour}"
            group = grouped.setdefault(
                key,
                {
                    "user_id": user_id,
                    "signature": signature,
                    "hour": hour,
                    "count": 0,
                    "weekday_counts": {},
                    "latest_ts": 0,
                    "latest_text": "",
                },
            )
            group["count"] += 1
            weekday = item.get("weekday")
            if weekday is not None:
                group["weekday_counts"][weekday] = group["weekday_counts"].get(weekday, 0) + 1
            ts = item.get("timestamp_ts") or 0
            if ts > group["latest_ts"]:
                group["latest_ts"] = ts
                group["latest_text"] = item.get("text", "")

        for group in grouped.values():
            if group["count"] < 3:
                continue
            recurrence_type, days_of_week = self._infer_recurrence(group)
            confidence = self._compute_confidence(group, recurrence_type, days_of_week)
            pattern = {
                "pattern_id": str(uuid.uuid4()),
                "kind": "autonomy_pattern",
                "user_id": group["user_id"],
                "signature": group["signature"],
                "hour": group["hour"],
                "days_of_week": ",".join([str(d) for d in days_of_week]) if days_of_week else None,
                "recurrence_type": recurrence_type,
                "confidence": confidence,
                "example_text": group["latest_text"],
                "last_seen_ts": group["latest_ts"],
                "last_generated_ts": 0,
                "accepted_count": 0,
                "rejected_count": 0,
                "updated_at_ts": int(time.time()),
            }
            await self._upsert_pattern(pattern)

    async def _execute_autonomous_task(self, pattern: Dict[str, Any], now: datetime) -> None:
        if not self._submit_query_callback:
            return
        query = pattern.get("example_text")
        if not query:
            return

        risk_level = self._classify_risk(query)
        request_id = str(uuid.uuid4())

        if risk_level == "high":
            approved = await self._request_permission(request_id, query, risk_level)
            if not approved:
                await self._update_pattern_feedback(pattern.get("pattern_id"), False)
                return
        elif risk_level == "medium":
            await self._emit_event(
                "autonomous_task_notice",
                request_id,
                {"query": query, "risk_level": risk_level},
            )

        await self._emit_event(
            "autonomous_task_started",
            request_id,
            {"query": query, "risk_level": risk_level},
        )

        try:
            task_id = await self._submit_query_callback(query, {"source": "autonomous"})
            self._autonomous_tasks[task_id] = {
                "pattern_id": pattern.get("pattern_id"),
                "signature": pattern.get("signature"),
                "user_id": pattern.get("user_id", "default_user"),
            }
            await self._update_payload(
                pattern["memory_id"],
                {"last_generated_ts": int(now.timestamp()), "updated_at_ts": int(time.time())},
            )
        except Exception as exc:
            await self._emit_event(
                "autonomous_task_result",
                request_id,
                {"status": "failed", "error": str(exc)},
            )

    async def _request_permission(self, request_id: str, query: str, risk_level: str) -> bool:
        future = asyncio.Future()
        self._permission_futures[request_id] = future
        await self._emit_event(
            "autonomous_permission_required",
            request_id,
            {"request_id": request_id, "query": query, "risk_level": risk_level},
        )
        try:
            approved = await asyncio.wait_for(future, timeout=60)
            return bool(approved)
        except asyncio.TimeoutError:
            return False
        finally:
            self._permission_futures.pop(request_id, None)

    def _pattern_due_now(self, pattern: Dict[str, Any], now: datetime) -> bool:
        target_hour = pattern.get("hour")
        if target_hour is None:
            return False
        last_generated_ts = int(pattern.get("last_generated_ts") or 0)
        if last_generated_ts:
            last_date = datetime.fromtimestamp(last_generated_ts, tz=now.tzinfo).date()
            if last_date == now.date():
                return False

        if now.hour != int(target_hour):
            return False
        if now.minute > 5:
            return False

        days_of_week = pattern.get("days_of_week")
        if days_of_week:
            allowed = {int(d) for d in str(days_of_week).split(",") if d != ""}
            if now.weekday() not in allowed:
                return False
        return True

    async def _upsert_pattern(self, pattern: Dict[str, Any]) -> None:
        filters = {
            "agent_id": self.agent_id,
            "kind": {"eq": "autonomy_pattern"},
            "signature": {"eq": pattern.get("signature")},
            "hour": {"eq": pattern.get("hour")},
        }
        if pattern.get("user_id"):
            filters["user_id"] = {"eq": pattern.get("user_id")}
        if pattern.get("days_of_week"):
            filters["days_of_week"] = {"eq": pattern.get("days_of_week")}
        existing = await self._list_by_filters(filters, limit=5)
        if existing:
            memory_id = existing[0]["memory_id"]
            updates = pattern.copy()
            updates.pop("pattern_id", None)
            await self._update_payload(memory_id, updates)
            return

        data = pattern.get("example_text", "")
        await asyncio.to_thread(
            self.memory.add,
            data,
            agent_id=self.agent_id,
            user_id=pattern.get("user_id", "default_user"),
            metadata=pattern,
            infer=False,
        )

    def _infer_recurrence(self, group: Dict[str, Any]) -> tuple[str, List[int]]:
        weekday_counts = group.get("weekday_counts", {})
        if not weekday_counts:
            return "none", []
        sorted_days = sorted(weekday_counts.items(), key=lambda x: x[1], reverse=True)
        top_day, top_count = sorted_days[0]
        distinct_days = len(weekday_counts.keys())

        if distinct_days >= 4:
            return "daily", list(weekday_counts.keys())
        if top_count >= 3:
            return "weekly", [top_day]
        return "none", []

    def _compute_confidence(
        self,
        group: Dict[str, Any],
        recurrence_type: str,
        days_of_week: List[int],
    ) -> float:
        count = group.get("count", 0)
        base = min(1.0, count / 5.0)
        day_factor = min(1.0, len(days_of_week) / 5.0) if days_of_week else 0.1
        recurrence_boost = 0.2 if recurrence_type in {"daily", "weekly"} else 0.0
        return min(0.95, base + day_factor * 0.3 + recurrence_boost)

    def _classify_risk(self, query: str) -> str:
        q = query.lower()
        high_keywords = ["delete", "remove", "erase", "purchase", "pay", "transfer", "shutdown", "format"]
        medium_keywords = ["send", "email", "message", "share", "post", "modify", "update", "run"]

        if any(k in q for k in high_keywords):
            return "high"
        if any(k in q for k in medium_keywords):
            return "medium"
        return "low"

    async def _update_pattern_feedback(self, pattern_id: Optional[str], accepted: bool) -> None:
        if not pattern_id:
            return
        filters = {
            "agent_id": self.agent_id,
            "kind": {"eq": "autonomy_pattern"},
            "pattern_id": {"eq": pattern_id},
        }
        patterns = await self._list_by_filters(filters, limit=1)
        if not patterns:
            return
        pattern = patterns[0]
        accepted_count = int(pattern.get("accepted_count") or 0)
        rejected_count = int(pattern.get("rejected_count") or 0)
        confidence = float(pattern.get("confidence") or 0.0)
        if accepted:
            accepted_count += 1
            confidence = min(0.98, confidence + 0.05)
        else:
            rejected_count += 1
            confidence = max(0.1, confidence - 0.1)
        await self._update_payload(
            pattern["memory_id"],
            {
                "accepted_count": accepted_count,
                "rejected_count": rejected_count,
                "confidence": confidence,
                "updated_at_ts": int(time.time()),
            },
        )

    async def _emit_event(self, event_type: str, task_id: str, payload: Dict[str, Any]) -> None:
        if not self._callbacks:
            return
        for cb in list(self._callbacks):
            try:
                await cb(event_type, task_id, payload)
            except Exception as exc:
                logger.warning("RemAgent callback error: %s", exc)

    async def _list_by_filters(self, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        async with self._lock:
            raw = await asyncio.to_thread(self.memory.vector_store.list, filters=filters, limit=limit)

        if not raw:
            return []
        if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], list):
            raw_items = raw[0]
        else:
            raw_items = raw

        items: List[Dict[str, Any]] = []
        for entry in raw_items:
            payload = entry.payload or {}
            items.append({"memory_id": entry.id, **payload})
        return items

    async def _get_by_reminder_id(self, reminder_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        filters = {
            "agent_id": self.agent_id,
            "user_id": user_id,
            "reminder_id": {"eq": reminder_id},
        }
        items = await self._list_by_filters(filters, limit=5)
        return items[0] if items else None

    async def _update_payload(self, memory_id: str, updates: Dict[str, Any]) -> None:
        async with self._lock:
            existing = await asyncio.to_thread(self.memory.vector_store.get, memory_id)
            payload = existing.payload or {}
            payload.update(updates)
            await asyncio.to_thread(self.memory.vector_store.update, memory_id, None, payload)

    def _ensure_tz(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return dt

    def _build_metadata(
        self,
        *,
        kind: str,
        reminder_id: str,
        text: str,
        label: Optional[str],
        trigger_dt: datetime,
        recurrence: Optional[Dict[str, Any]] = None,
        time_of_day: Optional[str] = None,
        days_of_week: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if recurrence and not time_of_day:
            time_of_day = trigger_dt.strftime("%H:%M")
        metadata = {
            "kind": kind,
            "reminder_id": reminder_id,
            "text": text,
            "label": label,
            "status": "scheduled",
            "trigger_at_ts": int(trigger_dt.timestamp()),
            "trigger_at_iso": trigger_dt.isoformat(),
            "created_at_ts": int(time.time()),
            "updated_at_ts": int(time.time()),
            "recurrence_type": "none",
            "recurrence_interval": 1,
            "days_of_week": ",".join(days_of_week) if days_of_week else None,
            "time_of_day": time_of_day,
        }
        if recurrence:
            metadata.update(self._recurrence_metadata(recurrence))
        return metadata

    def _recurrence_metadata(self, recurrence: Dict[str, Any]) -> Dict[str, Any]:
        r_type = (recurrence.get("type") or recurrence.get("frequency") or "none").lower()
        interval = recurrence.get("interval") or 1
        days = recurrence.get("days_of_week") or recurrence.get("days") or None
        return {
            "recurrence_type": r_type,
            "recurrence_interval": interval,
            "days_of_week": ",".join(days) if days else None,
            "recurrence_json": json.dumps(recurrence),
        }

    def _compute_next_alarm_time(
        self,
        time_str: str,
        days_of_week: Optional[List[str]],
        now: datetime,
    ) -> datetime:
        hour, minute = self._parse_time_of_day(time_str)
        if not days_of_week:
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        days = self._normalize_days_of_week(days_of_week)
        for i in range(0, 8):
            candidate_day = now + timedelta(days=i)
            if candidate_day.weekday() in days:
                candidate = candidate_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if candidate > now:
                    return candidate

        return now + timedelta(days=7)

    def _compute_next_recurrence(self, item: Dict[str, Any]) -> Optional[datetime]:
        recurrence_type = (item.get("recurrence_type") or "none").lower()
        interval = int(item.get("recurrence_interval") or 1)
        last_trigger = datetime.now().astimezone()

        if recurrence_type == "daily":
            return last_trigger + timedelta(days=interval)

        if recurrence_type == "weekly":
            days_str = item.get("days_of_week")
            if not days_str:
                return last_trigger + timedelta(weeks=interval)
            days = self._normalize_days_of_week(days_str.split(","))
            time_str = item.get("time_of_day") or last_trigger.strftime("%H:%M")
            return self._compute_next_alarm_time(time_str, [self._weekday_name(d) for d in days], last_trigger)

        return None

    def _parse_time_of_day(self, time_str: str) -> tuple[int, int]:
        parts = time_str.strip().split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        hour = int(parts[0])
        minute = int(parts[1])
        return hour, minute

    def _normalize_days_of_week(self, days: List[str]) -> List[int]:
        mapping = {
            "mon": 0,
            "monday": 0,
            "tue": 1,
            "tues": 1,
            "tuesday": 1,
            "wed": 2,
            "wednesday": 2,
            "thu": 3,
            "thurs": 3,
            "thursday": 3,
            "fri": 4,
            "friday": 4,
            "sat": 5,
            "saturday": 5,
            "sun": 6,
            "sunday": 6,
        }
        result = []
        for day in days:
            key = day.strip().lower()
            if key in mapping:
                result.append(mapping[key])
        return sorted(set(result)) or [datetime.now().weekday()]

    def _weekday_name(self, weekday: int) -> str:
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return names[weekday % 7]

    def _normalize_query(self, text: str) -> str:
        lowered = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text)
        return " ".join(lowered.split())

    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("reminder_id"),
            "kind": item.get("kind"),
            "text": item.get("text"),
            "label": item.get("label"),
            "status": item.get("status"),
            "trigger_at": item.get("trigger_at_iso"),
            "is_recurring": item.get("recurrence_type") not in (None, "none"),
        }
