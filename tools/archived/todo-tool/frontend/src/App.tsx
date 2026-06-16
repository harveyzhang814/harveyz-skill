import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { useState } from "react"
import { api } from "./lib/api"
import { AddTaskDialog } from "./components/AddTaskDialog"
import { FilterBar } from "./components/FilterBar"
import { TaskList } from "./components/TaskList"

const queryClient = new QueryClient()

function TodoApp() {
  const qc = useQueryClient()
  const [project, setProject] = useState("")
  const [priority, setPriority] = useState("")
  const [showDone, setShowDone] = useState(false)

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["tasks", { project, priority, status: showDone ? undefined : "todo" }],
    queryFn: () =>
      api.listTasks({
        project: project || undefined,
        priority: priority || undefined,
        status: showDone ? undefined : "todo",
      }),
  })

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  })

  const doneMutation = useMutation({
    mutationFn: (id: number) => api.updateTask(id, { status: "done" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  })

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Todo</h1>
        <AddTaskDialog
          projects={projects}
          onCreated={() => {
            qc.invalidateQueries({ queryKey: ["tasks"] })
            qc.invalidateQueries({ queryKey: ["projects"] })
          }}
        />
      </div>
      <FilterBar
        projects={projects}
        project={project}
        onProjectChange={setProject}
        priority={priority}
        onPriorityChange={setPriority}
        showDone={showDone}
        onShowDoneChange={setShowDone}
      />
      {isLoading ? (
        <p className="text-muted-foreground mt-6 text-sm">Loading...</p>
      ) : (
        <TaskList tasks={tasks} onDone={(id) => doneMutation.mutate(id)} />
      )}
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TodoApp />
    </QueryClientProvider>
  )
}
