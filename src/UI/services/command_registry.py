from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Command:
    id: str
    title: str
    handler: Callable[[], None]
    shortcut: str | None = None
    category: str = ""
    keywords: list[str] = field(default_factory=list)


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.id] = command

    def unregister(self, command_id: str) -> None:
        self._commands.pop(command_id, None)

    def execute(self, command_id: str) -> None:
        cmd = self._commands.get(command_id)
        if cmd:
            cmd.handler()

    def search(self, query: str) -> list[Command]:
        q = query.lower().strip()
        if not q:
            return list(self._commands.values())
        results: list[Command] = []
        seen: set[str] = set()
        for cmd in self._commands.values():
            if q in cmd.title.lower() or q in cmd.id.lower():
                results.append(cmd)
                seen.add(cmd.id)
                continue
            for kw in cmd.keywords:
                if q in kw.lower():
                    results.append(cmd)
                    break
        return results





