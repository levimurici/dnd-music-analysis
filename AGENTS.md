# AGENTS.md

Instruções para agentes (Codex, Cursor, Gemini CLI e outros que leem este arquivo).

As regras completas do projeto estão em **`CLAUDE.md`** (orquestrador) e cada etapa do fluxo está descrita em
`.claude/skills/<skill>/SKILL.md`:

1. `.claude/skills/estudo-completo/SKILL.md` — fluxo inteiro, em ordem
2. `.claude/skills/transpor-sax/SKILL.md` — partitura → ABC de concerto → sax alto/tenor (ABC + PDF)
3. `.claude/skills/analise-harmonica/SKILL.md` — análise tonal, funcional e melódica (estudo)
4. `.claude/skills/improvisacao-sax/SKILL.md` — escalas por trecho + folha para alto/tenor

Papéis auxiliares (rode como subagente se o seu agente tiver, ou siga as instruções você mesmo):
`.claude/agents/leitor-partitura.md` e `.claude/agents/revisor-estudo.md`.

Leia `CLAUDE.md` antes de começar e siga a skill da etapa pedida.
