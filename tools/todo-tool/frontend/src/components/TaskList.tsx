import type { Task } from "../lib/api"
import { TaskRow } from "./TaskRow"

interface Props {
  tasks: Task[]
  onDone: (id: number) => void
}

export function TaskList({ tasks, onDone }: Props) {
  if (tasks.length === 0) {
    return <p className="text-muted-foreground mt-6 text-sm">No tasks.</p>
  }

  const grouped = tasks.reduce<Record<string, Task[]>>((acc, t) => {
    ;(acc[t.project] ??= []).push(t)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([proj, projTasks]) => (
        <div key={proj}>
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            {proj}
          </h2>
          <div className="space-y-1">
            {projTasks.map((t) => (
              <TaskRow key={t.id} task={t} onDone={onDone} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
