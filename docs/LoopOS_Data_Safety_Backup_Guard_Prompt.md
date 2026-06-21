# LoopOS Data Safety / Backup Guard Kernel Prompt

版本：v0.1  
用途：给 Codex / Claude Code / OpenHands 使用，给当前 LoopOS 项目加入 **数据库与敏感数据保险机制**。  
目标：防止 Agent 在数据库迁移、表结构升级、批量写入、删除、敏感数据读取等操作中误删、误改、误迁移、泄露数据。  
定位：这是 LoopOS 的核心安全模块，应进入 **Policy OS + Syscall Layer + Outer Loop + Trace/Audit**。

---

## 0. 背景与必要性

AI coding agent 在执行数据库迁移、数据清理、批量更新、测试数据生成、schema 修改时，风险非常高。

典型危险场景：

```text
用户：
  帮我升级数据库结构。
  帮我迁移用户表。
  帮我清理重复订单。
  帮我重建索引。
  帮我修复生产数据库数据。
  帮我把旧系统数据迁到新表。
  帮我优化 Prisma/Alembic/Django/Rails migration。
```

如果 Agent 直接执行：

```sql
DROP TABLE users;
TRUNCATE orders;
DELETE FROM payments;
ALTER TABLE customers DROP COLUMN email;
UPDATE users SET role='admin';
```

后果可能是：

```text
生产数据丢失
隐私数据泄露
业务系统不可恢复
迁移脚本破坏 schema
测试环境污染生产环境
备份不可用
回滚路径不存在
Agent 误把 mock DB 当 prod DB
```

所以 LoopOS 必须加入保险机制：

> **凡是数据库和敏感数据操作，必须先备份、隔离、验证、再执行。**

---

# 1. 模块名称

建议模块名：

```text
Data Safety Kernel
```

或更有产品感：

```text
Backup Guard
```

内部包名：

```text
loopos/data_guard/
```

CLI 显示：

```text
LoopOS Backup Guard activated.
```

社区化名字可以叫：

```text
Guard Vault
```

中文：

```text
数据保险库 / 备份守护环
```

---

# 2. 总体原则

## 2.1 数据操作默认高风险

以下操作默认至少 L3：

```text
数据库迁移
schema 修改
表删除
字段删除
批量 update
批量 delete
truncate
drop
rename table
rename column
production DB connection
PII/secret 数据读取
跨环境数据复制
备份恢复
```

## 2.2 没有备份，不准执行

硬规则：

```text
No verified backup, no destructive data operation.
```

中文：

```text
没有已验证备份，不允许执行破坏性数据操作。
```

## 2.3 备份默认只读

备份产生后必须进入只读保险库：

```text
BackupVault
```

规则：

```text
1. 备份文件默认只读。
2. Agent 不能直接修改备份。
3. Agent 只能从备份创建临时测试副本。
4. 只有恢复流程可以读取备份进行 restore。
5. 备份读取也要记录 EventLog。
```

## 2.4 敏感数据最小化摄取

Agent 不应该直接把敏感数据放入模型上下文。

```text
敏感数据默认不进 LLM。
只允许：
- schema 摘要
- row count
- sample shape
- redacted sample
- checksum
- diff summary
```

只有在用户明确审批，并且 Policy OS 允许时，才可以读取更具体的数据。

## 2.5 先 dry-run / shadow-run

数据库迁移应先在 shadow database / temp clone 中执行：

```text
prod/staging DB
  ↓ backup
  ↓ restore to shadow DB
  ↓ run migration in shadow DB
  ↓ run tests/checks
  ↓ generate migration report
  ↓ user approval
  ↓ apply to target DB
```

## 2.6 回滚路径必须存在

对于高风险数据库操作，必须要求：

```text
rollback plan
restore command
backup location
schema diff
data validation checklist
```

没有 rollback plan，不允许执行。

---

# 3. 新增架构

```text
User Goal
  ↓
Goal Negotiation
  ↓
GoalSpec
  ↓
Policy OS
  ↓
Data Operation Detector
  ↓
Backup Guard
      ├── DB Connector Detector
      ├── Backup Planner
      ├── Backup Executor
      ├── Backup Verifier
      ├── ReadOnly Backup Vault
      ├── Shadow DB Restorer
      ├── Migration Runner
      ├── Data Validator
      ├── Rollback Planner
      └── Audit Logger
  ↓
Syscall Router
  ↓
Database / Files / Migration Tool
```

---

# 4. 新增模块结构

请新增：

```text
loopos/
  data_guard/
    __init__.py
    detector.py
    models.py
    policy.py
    backup_plan.py
    backup_executor.py
    backup_verifier.py
    vault.py
    shadow_db.py
    migration_runner.py
    validator.py
    rollback.py
    redaction.py
    audit.py

  syscalls/builtin/
    database.py

  cli/commands/
    data_guard.py
    db.py

policies/
  data/
    data_safety.yaml
    database_migration.yaml
    sensitive_data.yaml
```

测试：

```text
tests/data_guard/
  test_detector.py
  test_backup_plan.py
  test_backup_vault.py
  test_redaction.py
  test_policy.py
  test_shadow_db.py
  test_validator.py
  test_rollback.py
```

---

# 5. Data Operation Detector

目标：识别用户目标、命令、migration 文件、SQL 中的数据风险。

## 5.1 检测目标关键词

```text
database
db
migration
migrate
schema
table
column
index
prisma
alembic
django migration
rails migration
typeorm
sequelize
knex
flyway
liquibase
postgres
mysql
sqlite
mongodb
supabase
neon
planetscale

数据库
迁移
数据迁移
表
字段
索引
备份
恢复
生产库
测试库
清理数据
批量更新
批量删除
```

## 5.2 检测危险 SQL

危险 SQL pattern：

```sql
DROP DATABASE
DROP TABLE
DROP COLUMN
TRUNCATE
DELETE FROM
UPDATE ... without WHERE
ALTER TABLE
RENAME TABLE
CREATE INDEX CONCURRENTLY
VACUUM FULL
REINDEX
GRANT
REVOKE
COPY
LOAD DATA
```

高风险条件：

```text
DELETE without WHERE
UPDATE without WHERE
DROP / TRUNCATE
ALTER TABLE on large table
migration touching users/orders/payments/auth/session tables
production connection string detected
```

## 5.3 Detector 输出

```python
class DataOperationDetection(BaseModel):
    detected: bool
    operation_type: Literal[
        "schema_migration",
        "data_migration",
        "bulk_update",
        "bulk_delete",
        "backup",
        "restore",
        "sensitive_read",
        "unknown"
    ]
    risk_level: Literal["low", "medium", "high", "critical"]
    requires_backup: bool
    requires_shadow_run: bool
    requires_human_approval: bool
    sensitive_entities: list[str]
    matched_patterns: list[str]
    reason_codes: list[str]
```

---

# 6. Backup Plan

任何高风险数据操作必须先生成 BackupPlan。

```python
class BackupPlan(BaseModel):
    backup_plan_id: str
    run_id: str
    target_kind: Literal["postgres", "mysql", "sqlite", "mongodb", "file", "unknown"]
    target_name: str
    target_environment: Literal["local", "test", "staging", "production", "unknown"]
    backup_scope: Literal["full_database", "selected_tables", "schema_only", "data_only", "files"]
    tables: list[str]
    estimated_risk: Literal["low", "medium", "high", "critical"]
    backup_commands: list[str]
    verify_commands: list[str]
    restore_commands: list[str]
    backup_location: str
    read_only: bool
    requires_approval: bool
    created_at: datetime
```

规则：

```text
1. production/unknown environment 默认 high/critical。
2. destructive SQL 必须 full_database 或 affected tables backup。
3. migration touching sensitive tables requires selected table backup at minimum。
4. backup_location 必须在 .loopos/backups/ 或用户指定安全目录。
5. backup 文件命名必须带 timestamp + run_id + checksum。
```

---

# 7. Backup Vault

备份文件统一进入：

```text
.loopos/backups/
```

结构：

```text
.loopos/backups/
  run_01HZ/
    backup_manifest.json
    schema.sql
    data.dump
    checksums.txt
    restore_plan.md
    validation_report.json
```

BackupManifest：

```python
class BackupManifest(BaseModel):
    backup_id: str
    run_id: str
    created_at: datetime
    source: str
    environment: str
    files: list[str]
    checksums: dict[str, str]
    read_only: bool
    verified: bool
    verification_report: dict[str, Any]
    restore_plan_path: str
    policy_decision_id: str
```

Vault 规则：

```text
1. backup manifest 必须存在。
2. checksum 必须计算。
3. backup verified 后才允许继续 migration。
4. backup files chmod read-only where supported。
5. Agent cannot edit backup file.
6. Restoring from backup requires explicit restore syscall.
```

---

# 8. Shadow DB / Dry Run

高风险迁移必须先 shadow-run。

ShadowRunPlan：

```python
class ShadowRunPlan(BaseModel):
    shadow_run_id: str
    run_id: str
    backup_id: str
    shadow_target: str
    restore_from_backup: bool
    migration_commands: list[str]
    validation_commands: list[str]
    cleanup_commands: list[str]
    created_at: datetime
```

流程：

```text
1. Create backup.
2. Verify backup.
3. Restore backup to shadow DB or temp copy.
4. Run migration on shadow DB.
5. Run validation.
6. Generate report.
7. Ask user approval.
8. Apply to target DB only after approval.
```

如果无法创建 shadow DB：

```text
Policy OS must escalate to L3/L4.
Require explicit human approval.
Require manual backup confirmation.
```

---

# 9. Data Validation

迁移后必须验证：

```text
schema checks
row count checks
foreign key checks
not null checks
unique constraints
application tests
migration status
checksum where possible
sensitive data redaction
```

ValidationReport：

```python
class DataValidationReport(BaseModel):
    validation_id: str
    run_id: str
    backup_id: str | None
    target: str
    checks: list[dict[str, Any]]
    passed: bool
    warnings: list[str]
    failures: list[str]
    row_count_before: dict[str, int] = {}
    row_count_after: dict[str, int] = {}
    schema_diff_summary: str | None = None
    created_at: datetime
```

---

# 10. Sensitive Data Redaction

Agent 不能默认读取 PII 或 secret。

敏感字段 pattern：

```text
password
passwd
secret
token
api_key
apikey
access_key
refresh_token
session
cookie
ssn
id_card
phone
email
address
credit_card
card_number
bank
payment
salary
medical
health
```

Redaction 输出：

```python
class RedactedSample(BaseModel):
    table: str
    columns: list[str]
    rows: list[dict[str, Any]]
    redacted_fields: list[str]
    policy_decision_id: str
```

示例：

```json
{
  "email": "[REDACTED_EMAIL]",
  "phone": "[REDACTED_PHONE]",
  "token": "[REDACTED_SECRET]"
}
```

规则：

```text
1. LLM 默认只能看到 redacted sample。
2. raw sensitive data requires L4 user-only or explicit guarded approval。
3. backup vault may contain raw data but cannot be sent to model context。
4. trace logs must not contain raw secrets。
```

---

# 11. Policy OS 新增规则

新增 policies/data/data_safety.yaml。

## 11.1 Safety Levels

```text
L0:
  schema read
  table list
  row count
  migration status

L1:
  local sqlite test DB operation
  schema-only diff
  read-only metadata

L2:
  test/staging DB migration with backup
  local DB data update with backup

L3:
  production/staging destructive migration
  bulk update/delete
  restore operation
  unknown environment DB write

L4:
  raw sensitive data extraction
  customer PII export
  payment data access
  production data copy outside vault

L5:
  drop production database without backup
  truncate sensitive tables without backup
  delete without where on production
  exfiltrate secrets
```

## 11.2 硬规则

```text
1. destructive_data_operation_without_verified_backup -> block
2. production_db_write_without_approval -> block or L3 approval
3. sensitive_raw_data_to_model_context -> block
4. backup_file_write_after_verification -> block
5. migration_without_rollback_plan -> approval_required
6. unknown_environment_db_write -> high risk approval
7. drop_table_requires_full_backup -> approval_required
8. delete_without_where -> block unless explicit confirmed and backed up
```

---

# 12. Syscall 新增

新增 database syscalls：

```text
database.inspect
database.backup
database.verify_backup
database.restore_shadow
database.run_migration
database.validate
database.restore
database.redact_sample
database.diff_schema
```

每个 syscall 必须：

```text
1. build PolicyContext
2. require PolicyDecision
3. log Event
4. redact sensitive output
5. never leak secrets to trace
```

---

# 13. CLI 设计

新增命令：

```bash
loopos db detect --cmd "<sql or command>"
loopos db plan-backup --target <dsn-name>
loopos db backup --target <dsn-name>
loopos db verify-backup <backup_id>
loopos db shadow-run <migration>
loopos db validate <target>
loopos db restore --backup <backup_id>
loopos db audit <run_id>
```

## 13.1 迁移时 UI

```text
╭──────────────────── Backup Guard Activated ────────────────────╮
│ LoopOS detected a high-risk database operation.                  │
│ 小环狸提醒：先备份，再迁移。                                      │
╰────────────────────────────────────────────────────────────────╯

Detected:
  operation: schema_migration
  target: postgres://prod-db
  environment: production
  risk: critical

Required before execution:
  ✓ Backup plan
  ✓ Verified backup
  ✓ Shadow migration
  ✓ Validation report
  ✓ Human approval

Next:
  Create backup plan? [Y/n/details]
```

## 13.2 Backup 完成 UI

```text
╭──────────────────────── Backup Created ────────────────────────╮
│ Backup ID     backup_01HZ                                      │
│ Run ID        run_01HZM9                                       │
│ Target        production/users_db                              │
│ Scope         selected_tables                                  │
│ Tables        users, orders, payments                          │
│ Location      .loopos/backups/run_01HZ/                         │
│ Read-only     yes                                              │
│ Verified      yes                                              │
╰────────────────────────────────────────────────────────────────╯

Checksum:
  schema.sql   sha256:...
  data.dump    sha256:...

Restore:
  loopos db restore --backup backup_01HZ
```

## 13.3 Shadow Run UI

```text
[1] database.restore_shadow
  ✓ restored backup to shadow DB

[2] database.run_migration
  ✓ migration applied to shadow DB

[3] database.validate
  ✓ schema check passed
  ✓ row count check passed
  ✓ app tests passed

Decision:
  Migration is safe to apply to target.

Apply to target DB? [y/N/report]
```

---

# 14. Integration With Goal Negotiation

如果用户目标包含数据库风险：

```text
帮我升级数据库
帮我迁移用户表
帮我清理重复订单
```

Goal Proposal 必须包含一个安全方案：

```text
[1] 只读审计数据库迁移风险
    不执行迁移，只生成 backup/migration/rollback plan。

[2] 备份 + shadow run + validation
    创建备份，在 shadow DB 中试跑迁移，通过验证后再请求确认。

[3] 手动执行模式
    LoopOS 只生成命令和 checklist，不直接执行数据库写操作。
```

不能直接给：

```text
执行迁移
```

---

# 15. Integration With Loop Convergence

数据库任务的 acceptance criteria 必须包含：

```text
backup verified
shadow migration passed
validation passed
application tests passed
rollback plan exists
no sensitive data leaked to trace
```

EvaluationResult 示例：

```json
{
  "goal_satisfied": false,
  "acceptance_criteria_status": {
    "backup_verified": "passed",
    "shadow_migration_passed": "passed",
    "validation_passed": "failed",
    "rollback_plan_exists": "passed"
  },
  "score": 0.75,
  "failure_type": "data_validation_failed",
  "repairable": true
}
```

---

# 16. Integration With Memory Governance

可以写入：

```text
failure_pattern:
  database migration failed because validation row count mismatch

tool_profile:
  pg_dump backup for selected tables succeeded

project_rule:
  this project requires shadow migration before production DB changes
```

不能写入：

```text
raw customer data
database credentials
PII samples
unredacted secrets
```

---

# 17. Codex 实施提示词

## Phase A：Data Guard 设计文档

```text
You are adding Data Safety / Backup Guard Kernel to LoopOS.

Create docs/data-safety-backup-guard.md.

Document:
- why data operations are high risk
- backup-first policy
- read-only backup vault
- shadow DB / dry-run flow
- sensitive data redaction
- Policy OS rules
- database syscalls
- CLI UX
- integration with Goal Negotiation
- integration with Loop Convergence
- tests

Do not implement code yet.
```

## Phase B：Data Guard Models

```text
Implement loopos/data_guard/models.py.

Models:
- DataOperationDetection
- BackupPlan
- BackupManifest
- ShadowRunPlan
- DataValidationReport
- RedactedSample
- RestorePlan

Add tests:
tests/data_guard/test_models.py

No database connection.
No shell execution.
```

## Phase C：Detector

```text
Implement loopos/data_guard/detector.py.

Detect:
- database-related goals
- dangerous SQL
- migration commands
- sensitive table names
- production-like DSN strings

Add tests:
- DROP TABLE detected critical
- DELETE without WHERE detected high
- prisma migrate detected schema_migration
- "帮我升级数据库" detected
- normal pytest command not detected
```

## Phase D：Policy Pack

```text
Add policies/data/data_safety.yaml.

Update Policy OS to understand data operation context.

Rules:
- destructive operation without verified backup -> blocked
- raw sensitive data to model context -> blocked
- production write without approval -> blocked or high approval
- backup file mutation after verification -> blocked
- shadow run recommended for migration

Add tests:
tests/policy_os/test_data_safety_policy.py
```

## Phase E：Backup Vault

```text
Implement loopos/data_guard/vault.py.

Features:
- create backup directory
- write BackupManifest
- compute checksums
- mark read-only where supported
- verify manifest
- prevent mutation through LoopOS APIs

No real DB dump yet.
Use sample files in tests.

Tests:
- manifest created
- checksum verified
- missing file fails verification
- read-only flag recorded
```

## Phase F：Redaction

```text
Implement loopos/data_guard/redaction.py.

Features:
- detect sensitive columns
- redact emails, phones, tokens, passwords
- produce RedactedSample
- ensure trace-safe output

Tests:
- email redacted
- token redacted
- password redacted
- non-sensitive fields preserved
```

## Phase G：Database Syscall Skeleton

```text
Implement loopos/syscalls/builtin/database.py.

Syscalls:
- database.inspect
- database.backup
- database.verify_backup
- database.restore_shadow
- database.run_migration
- database.validate
- database.restore
- database.redact_sample
- database.diff_schema

For v0:
- use mock adapter
- no real DB connection
- no real destructive operation

All syscalls must pass Policy OS.
```

## Phase H：CLI

```text
Add loopos/cli/commands/db.py.

Commands:
- loopos db detect --cmd "<sql>"
- loopos db plan-backup --target <name>
- loopos db backup --target <name>
- loopos db verify-backup <backup_id>
- loopos db shadow-run <migration>
- loopos db validate <target>
- loopos db audit <run_id>

Add Rich renderers:
- BackupGuardRenderer
- BackupPlanRenderer
- BackupManifestRenderer
- ShadowRunRenderer
- ValidationReportRenderer

Tests:
- db detect dangerous SQL
- db backup mock creates manifest
- db verify works
```

## Phase I：Goal / Loop Integration

```text
Update Goal Negotiation:
If goal is database-related, proposals must include:
1. read-only audit
2. backup + shadow run + validation
3. manual execution checklist

Update Loop Convergence:
Database tasks require acceptance criteria:
- backup verified
- shadow migration passed
- validation passed
- rollback plan exists
- no sensitive data leaked

Tests:
- "帮我升级数据库" shows data-safe proposals
- database GoalSpec contains backup acceptance criteria
- loop cannot execute database migration without BackupManifest verified
```

---

# 18. 最终验收标准

完成后，以下行为必须成立。

## 18.1 危险 SQL 被识别

```bash
loopos db detect --cmd "DROP TABLE users;"
```

输出：

```text
operation: schema_migration
risk: critical
requires_backup: true
requires_shadow_run: true
requires_human_approval: true
```

## 18.2 没有备份不准迁移

```bash
loopos run "帮我执行数据库迁移"
```

必须先进入 Backup Guard：

```text
Backup Guard Activated
Required:
- backup plan
- verified backup
- shadow migration
- validation report
- human approval
```

不能直接执行 migration。

## 18.3 备份只读

BackupManifest 必须记录：

```text
read_only: true
verified: true
checksums
restore_plan
```

## 18.4 敏感数据不进上下文

如果读取 users 表 sample：

```json
{
  "email": "[REDACTED_EMAIL]",
  "token": "[REDACTED_SECRET]"
}
```

Trace 不得出现 raw token/password。

## 18.5 Shadow run 后再执行

迁移流程必须是：

```text
backup
verify backup
restore shadow
run migration on shadow
validate
ask approval
apply target
validate target
```

---

# 19. 推荐优先级

这个模块应该作为 P0.5 加入，也就是：

```text
Phase 5 Safety Levels 之后
Phase 6 Local Intelligence 之前
```

原因：

```text
数据库误操作是 Agent 工具最容易造成真实损失的场景。
这个能力会显著提升 LoopOS 的可信度和差异化。
```

建议插入现有路线：

```text
Phase 0  current-repo-improvement-plan
Phase 1  CLI split
Phase 2  CLI UI
Phase 3  Goal Negotiation v1
Phase 4  Loop Convergence v1
Phase 5  Safety Levels
Phase 5.5 Data Safety / Backup Guard
Phase 6  Local Intelligence
Phase 7  Registry
...
```

---

# 20. 一句话总结

LoopOS 必须坚持：

> **Agent 可以帮你改数据库，但不能在没有备份、没有 shadow run、没有验证、没有回滚计划、没有用户确认的情况下碰真实数据。**

这就是 LoopOS 和普通 coding agent 的关键差异：

```text
普通 Agent：
  “我试试看。”

LoopOS：
  “先备份，先验证，先过 Policy，再执行。”
```
