import { Task } from "../lib/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Check } from "lucide-react"

const PRIORITY_VARIANT: Record<string, "destructive" | "default" | "secondary" | "outline"> = {
  P0: "destructive",
  P1: "default",
  P2: "secondary",
  P3: "outline",
}

interface Props {
  task: Task
  onDone: (id: number) => void
}

export function TaskRow({ task, onDone }: Props) {
  const isDone = task.status === "done"
  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border ${
        isDone ? "opacity-50" : ""
      }`}
    >
      <div className="flex items-center gap-3 min-w-0">
        <Badge variant={PRIORITY_VARIANT[task.priority] ?? "outline"}>
          {task.priority}
        </Badge>
        <span className={`truncate ${isDone ? "line-through text-muted-foreground" : ""}`}>
          {task.title}
        </span>
      </div>
      <div className="flex items-center gap-2 ml-2 shrink-0 text-xs text-muted-foreground">
        <span>{task.created_at.slice(0, 10)}</span>
        {!isDone && (
          <Button size="sm" variant="ghost" onClick={() => onDone(task.id)}>
            <Check className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
