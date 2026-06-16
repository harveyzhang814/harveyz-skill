const BASE = "/api"

export interface Task {
  id: number
  title: string
  project: string
  priority: string
  status: string
  created_at: string
}

export interface TaskCreate {
  title: string
  project: string
  priority?: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  if (r.status === 204) return undefined as T
  return r.json()
}

export const api = {
  listTasks: (params: { project?: string; status?: string; priority?: string } = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v) as [string, string][]
    )
    return request<Task[]>(`/tasks?${q}`)
  },
  createTask: (data: TaskCreate) =>
    request<Task>("/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id: number, data: Partial<Task>) =>
    request<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTask: (id: number) =>
    request<void>(`/tasks/${id}`, { method: "DELETE" }),
  listProjects: () => request<string[]>("/projects"),
}
