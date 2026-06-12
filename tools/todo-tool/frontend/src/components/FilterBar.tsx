import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"

interface Props {
  projects: string[]
  project: string
  onProjectChange: (v: string) => void
  priority: string
  onPriorityChange: (v: string) => void
  showDone: boolean
  onShowDoneChange: (v: boolean) => void
}

export function FilterBar({
  projects,
  project,
  onProjectChange,
  priority,
  onPriorityChange,
  showDone,
  onShowDoneChange,
}: Props) {
  return (
    <div className="flex gap-2 mb-4 flex-wrap">
      <Select
        value={project || "all"}
        onValueChange={(v) => onProjectChange(v === "all" ? "" : v)}
      >
        <SelectTrigger className="w-44">
          <SelectValue placeholder="All Projects" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Projects</SelectItem>
          {projects.map((p) => (
            <SelectItem key={p} value={p}>
              {p}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={priority || "all"}
        onValueChange={(v) => onPriorityChange(v === "all" ? "" : v)}
      >
        <SelectTrigger className="w-40">
          <SelectValue placeholder="All Priorities" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Priorities</SelectItem>
          {["P0", "P1", "P2", "P3"].map((p) => (
            <SelectItem key={p} value={p}>
              {p}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        variant={showDone ? "secondary" : "outline"}
        size="sm"
        onClick={() => onShowDoneChange(!showDone)}
      >
        {showDone ? "Hide Done" : "Show Done"}
      </Button>
    </div>
  )
}
