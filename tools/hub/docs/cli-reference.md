# hub CLI Reference

**Entry point:** `hub`

---

## Top-level

```
hub [--help]
```

| Subcommand | Description |
|---|---|
| `projects` | Manage registered projects |
| `tasks` | Manage tasks |
| `git` | Git operations on registered projects |

---

## projects

```
hub projects <command>
```

### list

List all registered projects.

```
hub projects list [--json]
```

### add

Register or update a project.

```
hub projects add <name> [--path TEXT] [--desc TEXT] [--json]
```

| Argument/Option | Description |
|---|---|
| `name` | Project name (GitHub repo name) |
| `--path` | Local directory path |
| `--desc` | Short description |

### path

Print the local path for a project (for shell `cd` / agent use).

```
hub projects path <name> [--json]
```

### sync

Re-scan configured dirs and update `PROJECTS.md`. Requires p-launch config.

```
hub projects sync [--json]
```

### scan

Scan directories for git repos and register them as projects.

```
hub projects scan <dirs...> [--json]
```

| Argument | Description |
|---|---|
| `dirs` | One or more directories to scan for git repos |

### remove

Remove a project from the registry.

```
hub projects remove <name> [--force] [--json]
```

| Option | Description |
|---|---|
| `--force` | Also delete associated tasks |

---

## tasks

```
hub tasks <command>
```

### list

List tasks, optionally filtered.

```
hub tasks list [-p PROJECT] [-s STATUS] [-P PRIORITY] [--json]
```

| Option | Description |
|---|---|
| `-p / --project` | Filter by project name |
| `-s / --status` | Filter by status |
| `-P / --priority` | Filter by priority |

### add

Add a new task.

```
hub tasks add <title> -p PROJECT [-P PRIORITY] [--json]
```

| Argument/Option | Description |
|---|---|
| `title` | Task title |
| `-p / --project` | Project name (required) |
| `-P / --priority` | Priority (default: `P2`) |

### done

Mark a task as done.

```
hub tasks done <task_id> [--json]
```

### update

Update task fields.

```
hub tasks update <task_id> [--title TEXT] [--priority TEXT] [--status TEXT] [--json]
```

### rm

Delete a task.

```
hub tasks rm <task_id> [--json]
```

---

## git

```
hub git <command>
```

All git commands accept `-p / --project` to target a specific registered project. Defaults to the current working directory's project.

### status

Show branch, working tree, and recent commits.

```
hub git status [-p PROJECT] [-n COMMITS]
```

| Option | Description |
|---|---|
| `-n / --commits` | Number of recent commits to show (default: 5) |

### fetch

Fetch all remotes.

```
hub git fetch [-p PROJECT]
```

### branches

List branches with upstream sync status.

```
hub git branches [-p PROJECT]
```

### pull

Pull a branch from its remote upstream.

```
hub git pull [-p PROJECT] [-b BRANCH]
```

| Option | Description |
|---|---|
| `-b / --branch` | Branch to pull (default: current branch) |

### push

Push a branch to its remote upstream.

```
hub git push [-p PROJECT] [-b BRANCH]
```

| Option | Description |
|---|---|
| `-b / --branch` | Branch to push (default: current branch) |
