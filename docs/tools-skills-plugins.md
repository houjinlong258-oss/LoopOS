# Tools, Skills, Plugins

LoopOS borrows the tools/skills/plugins layering pattern but keeps it tied to
project training.

| Layer | Meaning |
| --- | --- |
| Tool | typed callable action that can change project state |
| Skill | reusable project-training instruction pack |
| Plugin | optional extension adding providers, tools, adapters, hooks, or skills |

`ToolCatalogSearch` prevents dumping every tool schema into every prompt. It
returns only tools relevant to the current query and reports estimated token
savings.
