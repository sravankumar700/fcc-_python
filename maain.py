"""A small command-line task manager with JSON persistence.

This file is intentionally self-contained so it can be run directly with
``python maain.py``.  It demonstrates classes, validation, file handling,
sorting, searching, and a simple interactive menu.
"""


DATA_FILE = Path.home() / ".python_tasks.json"
DATE_FORMAT = "%Y-%m-%d"
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"pending", "in-progress", "done"}


def today_string() -> str:
	"""Return today's date in the format used by stored tasks."""
	return date.today().strftime(DATE_FORMAT)


def parse_date(value: str) -> str:
	"""Validate and normalize a date string."""
	value = value.strip()
	datetime.strptime(value, DATE_FORMAT)
	return value


def clean_text(value: str, field_name: str) -> str:
	"""Validate required text input."""
	value = value.strip()
	if not value:
		raise ValueError(f"{field_name} cannot be empty")
	return value


@dataclass
class Task:
	"""A single task in the task list."""

	task_id: int
	title: str
	description: str = ""
	priority: str = "medium"
	status: str = "pending"
	due_date: Optional[str] = None
	tags: list[str] = field(default_factory=list)
	created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
	completed_at: Optional[str] = None

	def __post_init__(self) -> None:
		self.title = clean_text(self.title, "Title")
		self.description = self.description.strip()
		self.priority = self.priority.lower().strip()
		self.status = self.status.lower().strip()
		if self.priority not in VALID_PRIORITIES:
			raise ValueError("Priority must be low, medium, or high")
		if self.status not in VALID_STATUSES:
			raise ValueError("Status must be pending, in-progress, or done")
		if self.due_date:
			self.due_date = parse_date(self.due_date)
		self.tags = sorted({tag.strip().lower() for tag in self.tags if tag.strip()})

	@property
	def is_overdue(self) -> bool:
		"""Whether the task is unfinished and past its due date."""
		return bool(self.due_date and self.status != "done" and self.due_date < today_string())

	def mark_done(self) -> None:
		self.status = "done"
		self.completed_at = datetime.now().isoformat(timespec="seconds")

	def reopen(self) -> None:
		self.status = "pending"
		self.completed_at = None

	def short_line(self) -> str:
		marker = "x" if self.status == "done" else " "
		overdue = " OVERDUE" if self.is_overdue else ""
		due = f" | due {self.due_date}" if self.due_date else ""
		return f"[{marker}] #{self.task_id} {self.title} ({self.priority}){due}{overdue}"

	def detailed_text(self) -> str:
		tags = ", ".join(self.tags) or "none"
		lines = [
			f"ID:          {self.task_id}",
			f"Title:       {self.title}",
			f"Description: {self.description or 'none'}",
			f"Priority:    {self.priority}",
			f"Status:      {self.status}",
			f"Due date:    {self.due_date or 'none'}",
			f"Tags:        {tags}",
			f"Created:     {self.created_at}",
			f"Completed:   {self.completed_at or 'not completed'}",
		]
		return "\n".join(lines)

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> "Task":
		return cls(
			task_id=int(data["task_id"]),
			title=str(data["title"]),
			description=str(data.get("description", "")),
			priority=str(data.get("priority", "medium")),
			status=str(data.get("status", "pending")),
			due_date=data.get("due_date"),
			tags=list(data.get("tags", [])),
			created_at=str(data.get("created_at", datetime.now().isoformat(timespec="seconds"))),
			completed_at=data.get("completed_at"),
		)


class TaskManager:
	"""Manage tasks and persist them as JSON."""

	def __init__(self, path: Path = DATA_FILE) -> None:
		self.path = path
		self.tasks: list[Task] = []
		self.load()

	def load(self) -> None:
		if not self.path.exists():
			self.tasks = []
			return
		try:
			raw = json.loads(self.path.read_text(encoding="utf-8"))
			self.tasks = [Task.from_dict(item) for item in raw]
		except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
			print(f"Could not load tasks: {error}")
			self.tasks = []

	def save(self) -> None:
		self.path.parent.mkdir(parents=True, exist_ok=True)
		temporary = self.path.with_suffix(".tmp")
		temporary.write_text(json.dumps([asdict(task) for task in self.tasks], indent=2), encoding="utf-8")
		temporary.replace(self.path)

	def next_id(self) -> int:
		return max((task.task_id for task in self.tasks), default=0) + 1

	def add(self, title: str, description: str = "", priority: str = "medium",
			due_date: Optional[str] = None, tags: Iterable[str] = ()) -> Task:
		task = Task(self.next_id(), title, description, priority, "pending", due_date, list(tags))
		self.tasks.append(task)
		self.save()
		return task

	def get(self, task_id: int) -> Task:
		for task in self.tasks:
			if task.task_id == task_id:
				return task
		raise LookupError(f"No task with ID {task_id}")

	def remove(self, task_id: int) -> Task:
		task = self.get(task_id)
		self.tasks.remove(task)
		self.save()
		return task

	def complete(self, task_id: int) -> Task:
		task = self.get(task_id)
		task.mark_done()
		self.save()
		return task

	def reopen(self, task_id: int) -> Task:
		task = self.get(task_id)
		task.reopen()
		self.save()
		return task

	def search(self, phrase: str = "", status: Optional[str] = None,
			   priority: Optional[str] = None, tag: Optional[str] = None) -> list[Task]:
		phrase = phrase.lower().strip()
		tag = tag.lower().strip() if tag else None
		return [
			task for task in self.tasks
			if (not phrase or phrase in task.title.lower() or phrase in task.description.lower())
			and (not status or task.status == status)
			and (not priority or task.priority == priority)
			and (not tag or tag in task.tags)
		]

	def sorted_tasks(self, tasks: Iterable[Task], sort_by: str = "id") -> list[Task]:
		keys = {
			"id": lambda task: task.task_id,
			"title": lambda task: task.title.lower(),
			"priority": lambda task: ("high", "medium", "low").index(task.priority),
			"due": lambda task: task.due_date or "9999-12-31",
			"status": lambda task: task.status,
		}
		return sorted(tasks, key=keys.get(sort_by, keys["id"]))

	def statistics(self) -> dict[str, int]:
		result = {"total": len(self.tasks), "done": 0, "pending": 0, "in-progress": 0, "overdue": 0}
		for task in self.tasks:
			result[task.status] += 1
			result["overdue"] += int(task.is_overdue)
		return result

	def backup(self) -> Path:
		backup_path = self.path.with_suffix(".backup.json")
		if self.path.exists():
			shutil.copy2(self.path, backup_path)
		else:
			backup_path.write_text("[]", encoding="utf-8")
		return backup_path


def ask(prompt: str, default: Optional[str] = None) -> str:
	suffix = f" [{default}]" if default is not None else ""
	answer = input(f"{prompt}{suffix}: ").strip()
	return answer if answer else (default or "")


def ask_id() -> int:
	while True:
		try:
			return int(ask("Task ID"))
		except ValueError:
			print("Please enter a number.")


def print_tasks(tasks: Iterable[Task]) -> None:
	tasks = list(tasks)
	if not tasks:
		print("No matching tasks.")
		return
	for task in tasks:
		print(task.short_line())


def add_task(manager: TaskManager) -> None:
	title = ask("Title")
	description = ask("Description")
	priority = ask("Priority (low/medium/high)", "medium")
	due = ask("Due date (YYYY-MM-DD, blank for none)") or None
	tags = ask("Tags separated by commas")
	task = manager.add(title, description, priority, due, tags.split(","))
	print(f"Added task #{task.task_id}.")


def list_tasks(manager: TaskManager) -> None:
	phrase = ask("Search text")
	status = ask("Status filter (blank for all)") or None
	priority = ask("Priority filter (blank for all)") or None
	sort_by = ask("Sort by id/title/priority/due/status", "id")
	tasks = manager.search(phrase, status, priority)
	print_tasks(manager.sorted_tasks(tasks, sort_by))


def show_statistics(manager: TaskManager) -> None:
	stats = manager.statistics()
	print("\nTask statistics")
	for name, value in stats.items():
		print(f"{name.title():12} {value}")


def interactive(manager: TaskManager) -> None:
	menu = """
1. Add task
2. List/search tasks
3. View task
4. Complete task
5. Reopen task
6. Delete task
7. Statistics
8. Backup data
9. Quit
"""
	actions = {
		"1": lambda: add_task(manager),
		"2": lambda: list_tasks(manager),
		"3": lambda: print(manager.get(ask_id()).detailed_text()),
		"4": lambda: print(f"Completed task #{manager.complete(ask_id()).task_id}."),
		"5": lambda: print(f"Reopened task #{manager.reopen(ask_id()).task_id}."),
		"6": lambda: print(f"Deleted task #{manager.remove(ask_id()).task_id}."),
		"7": lambda: show_statistics(manager),
		"8": lambda: print(f"Backup created at {manager.backup()}"),
	}
	while True:
		print(menu)
		choice = input("Choose an option: ").strip()
		if choice == "9":
			print("Goodbye!")
			return
		action = actions.get(choice)
		if not action:
			print("Invalid option.")
			continue
		try:
			action()
		except (ValueError, LookupError, OSError) as error:
			print(f"Error: {error}")


def main() -> None:
	"""Start the application."""
	if "--reset" in sys.argv:
		if DATA_FILE.exists():
			DATA_FILE.unlink()
		print("Task data reset.")
		return
	manager = TaskManager()
	interactive(manager)


if __name__ == "__main__":
	main()
