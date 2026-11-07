from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Node:
    label: str
    children: List["Node"] = field(default_factory=list)
    token: Optional[object] = None

    def add(self,child: "Node") -> "Node":
        self.children.append(child)
        return self

    def pretty(self,prefix: str = "", last: bool = True, root: bool = True) -> str :
        text = self.label if self.token is None else f"{self.label} «{self.token.value}»"
        if root:
            lines = [text]
            child_prefix = ""
        else:
            lines = [prefix + ("└── " if last else "├── ") + text]
            child_prefix = prefix + ("    " if last else "│   ")
        for i,c in enumerate(self.children):
            lines.append(c.pretty(child_prefix, i == len(self.children) - 1, False))
        return "\n".join(lines)

    def to_sexpr(self) -> str:
        """Notación entre paréntesis (solo para pruebas y depuración)."""
        if self.token is not None:
            return f"[{self.token.value}]"
        return f"({self.label} " + " ".join(c.to_sexpr() for c in self.children) + ")"