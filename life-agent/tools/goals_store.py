import json
import uuid
from datetime import datetime
from pathlib import Path

GOALS_FILE = Path(__file__).parent.parent / "data" / "goals.json"


def _load() -> dict:
    return json.loads(GOALS_FILE.read_text(encoding="utf-8"))


def _save(data: dict):
    GOALS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def get_all() -> list[dict]:
    return _load().get("goals", [])


def get_active() -> list[dict]:
    return [g for g in get_all() if g.get("status") == "active"]


def add_goal(title: str, description: str, category: str, deadline: str,
             milestones: list[str]) -> dict:
    data = _load()
    goal = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "description": description,
        "category": category,
        "deadline": deadline,
        "milestones": [{"text": m, "done": False} for m in milestones],
        "progress": 0,
        "check_ins": [],
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    data["goals"].append(goal)
    _save(data)
    return goal


def log_check_in(goal_id: str, note: str, progress: int):
    data = _load()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            goal["check_ins"].append({
                "date": datetime.now().isoformat(),
                "note": note,
                "progress": progress,
            })
            goal["progress"] = progress
            break
    _save(data)


def complete_milestone(goal_id: str, milestone_index: int):
    data = _load()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            goal["milestones"][milestone_index]["done"] = True
            done = sum(1 for m in goal["milestones"] if m["done"])
            total = len(goal["milestones"])
            goal["progress"] = int((done / total) * 100) if total else 0
            break
    _save(data)


def update_status(goal_id: str, status: str):
    data = _load()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            goal["status"] = status
            break
    _save(data)


def get_goal(goal_id: str) -> dict | None:
    return next((g for g in get_all() if g["id"] == goal_id), None)


def _herbereken(goal: dict) -> None:
    ms = goal.get("milestones", [])
    if ms:
        goal["progress"] = int(sum(1 for m in ms if m["done"]) / len(ms) * 100)


def update_goal(goal_id: str, **velden) -> dict | None:
    """Werk title/description/category/deadline/status bij (alleen meegegeven velden)."""
    data = _load()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            for k in ("title", "description", "category", "deadline", "status"):
                if velden.get(k) is not None:
                    goal[k] = velden[k]
            if velden.get("status") == "completed":
                goal["completed_at"] = datetime.now().isoformat()
            _save(data)
            return goal
    return None


def toggle_milestone(goal_id: str, index: int) -> dict | None:
    data = _load()
    for goal in data["goals"]:
        if goal["id"] == goal_id and 0 <= index < len(goal["milestones"]):
            goal["milestones"][index]["done"] = not goal["milestones"][index]["done"]
            _herbereken(goal)
            _save(data)
            return goal
    return None


def add_milestone(goal_id: str, text: str) -> dict | None:
    data = _load()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            goal.setdefault("milestones", []).append({"text": text, "done": False})
            _herbereken(goal)
            _save(data)
            return goal
    return None


def remove_milestone(goal_id: str, index: int) -> dict | None:
    data = _load()
    for goal in data["goals"]:
        if goal["id"] == goal_id and 0 <= index < len(goal["milestones"]):
            goal["milestones"].pop(index)
            _herbereken(goal)
            _save(data)
            return goal
    return None


def format_goals_summary() -> str:
    goals = get_active()
    if not goals:
        return "Geen actieve doelen."
    lines = []
    for g in goals:
        done = sum(1 for m in g["milestones"] if m["done"])
        total = len(g["milestones"])
        lines.append(f"[{g['id']}] {g['title']} — {g['progress']}% — deadline {g['deadline']} — {done}/{total} mijlpalen")
    return "\n".join(lines)
