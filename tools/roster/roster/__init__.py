"""roster —— 人（creator）与渠道（channel）名册。

三份数据、三个消费者、三个 CLI 命令组：
  registry.json    人与渠道的定义   manage-roster skill
  state.json       游标与失败态     sync-* skill
  profiles/*.md    画像             认知层 skill

渠道数据可重建，画像不可重建。这条线决定了它们为什么分三份存。
"""

SCHEMA_VERSION = 1
