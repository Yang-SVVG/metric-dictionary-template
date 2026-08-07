-- 指标字典：表结构
-- 方言：MySQL 8.0（SQLite 也可跑，去掉 COMMENT 与 ENGINE 即可）
-- 设计要点：
--   1) 指标定义与版本分离，口径变更留痕，历史报表可追溯；
--   2) 来源表单独登记血缘，公式里的表必须能在血缘里找到；
--   3) 状态机收敛为 draft / active / deprecated 三态。

CREATE TABLE dim_metric (
    metric_code     VARCHAR(64)  NOT NULL COMMENT '指标编码，snake_case，全局唯一',
    metric_name     VARCHAR(128) NOT NULL COMMENT '指标中文名',
    domain          VARCHAR(32)  NOT NULL COMMENT '业务域：经营/用户/供应链/财务/质量',
    definition      TEXT         NOT NULL COMMENT '一句话定义，必须能被业务方复述',
    formula         TEXT         NOT NULL COMMENT '可执行口径（SQL 片段或表达式）',
    grain           VARCHAR(16)  NOT NULL COMMENT '统计粒度：日/周/月',
    unit            VARCHAR(16)  NOT NULL COMMENT '单位：元/人/%/天',
    owner           VARCHAR(64)  NOT NULL COMMENT '口径负责人（团队或个人）',
    status          VARCHAR(16)  NOT NULL DEFAULT 'draft' COMMENT 'draft/active/deprecated',
    current_version VARCHAR(16)  NOT NULL DEFAULT 'v1.0',
    updated_at      DATETIME     NOT NULL,
    PRIMARY KEY (metric_code),
    KEY idx_domain_status (domain, status)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '指标字典主表';

CREATE TABLE dim_metric_version (
    metric_code  VARCHAR(64)  NOT NULL,
    version      VARCHAR(16)  NOT NULL,
    definition   TEXT         NOT NULL COMMENT '该版本的完整定义快照',
    formula      TEXT         NOT NULL COMMENT '该版本的公式快照',
    change_note  VARCHAR(255) NOT NULL COMMENT '变更原因，必须写清为什么改',
    approved_by  VARCHAR(64)  NOT NULL COMMENT '评审人',
    effective_at DATETIME     NOT NULL COMMENT '生效时间，报表口径以此为准',
    PRIMARY KEY (metric_code, version),
    CONSTRAINT fk_version_metric FOREIGN KEY (metric_code) REFERENCES dim_metric (metric_code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '指标口径版本表';

CREATE TABLE dim_metric_lineage (
    metric_code  VARCHAR(64)  NOT NULL,
    source_table VARCHAR(128) NOT NULL COMMENT '物理表名',
    join_type    VARCHAR(16)  NOT NULL DEFAULT 'from' COMMENT 'from/join',
    note         VARCHAR(255) NULL,
    PRIMARY KEY (metric_code, source_table, join_type),
    CONSTRAINT fk_lineage_metric FOREIGN KEY (metric_code) REFERENCES dim_metric (metric_code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '指标血缘：公式里出现的表必须登记在这里';

-- 供报表直接查询的宽视图：只暴露生效口径
CREATE VIEW v_active_metric AS
SELECT metric_code, metric_name, domain, definition, formula, grain, unit, owner, current_version
FROM dim_metric
WHERE status = 'active';
